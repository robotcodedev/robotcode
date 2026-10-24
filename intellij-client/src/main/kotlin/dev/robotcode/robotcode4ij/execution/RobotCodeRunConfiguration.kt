package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.CantRunException
import com.intellij.execution.Executor
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.RefactoringListenerProvider
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.RuntimeConfigurationError
import com.intellij.execution.configurations.RuntimeConfigurationException
import com.intellij.execution.configurations.RuntimeConfigurationWarning
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.testframework.sm.runner.SMRunnerConsolePropertiesProvider
import com.intellij.execution.testframework.sm.runner.SMTRunnerConsoleProperties
import com.intellij.execution.util.ProgramParametersConfigurator
import com.intellij.openapi.options.SettingsEditor
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.JDOMExternalizerUtil
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFileSystemItem
import com.intellij.refactoring.listeners.RefactoringElementListener
import com.intellij.util.IncorrectOperationException
import com.jetbrains.python.run.AbstractPythonRunConfiguration
import com.jetbrains.python.run.DebugAwareConfiguration
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.actions.RobotCodeConfigurePythonInterpreterAction
import dev.robotcode.robotcode4ij.configuration.ProfileList
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.configuration.profileListCache
import dev.robotcode.robotcode4ij.pythonInterpreterOf
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import dev.robotcode.robotcode4ij.robotPythonModule
import dev.robotcode.robotcode4ij.testing.testManger
import org.jdom.Element
import java.nio.file.InvalidPathException
import java.nio.file.Path

/**
 * A Robot Framework run configuration. It is a PyCharm Python run configuration, so it has PyCharm's interpreter,
 * environment and working-directory options, and stores what it runs, its target, in
 * [RobotCodeRunConfigurationOptions].
 */
class RobotCodeRunConfiguration(project: Project, factory: ConfigurationFactory) :
    AbstractPythonRunConfiguration<RobotCodeRunConfiguration>(project, factory), SMRunnerConsolePropertiesProvider,
    DebugAwareConfiguration, RefactoringListenerProvider {

    init {
        applyRobotCodeDefaults()
    }

    // runs as before: the interpreter that RobotCode uses for the language server, the project folder as working
    // directory and no PYTHONPATH entries from the project's roots; earlier versions stored no interpreter options,
    // which PyCharm's editor needs as a value
    private fun applyRobotCodeDefaults() {
        project.robotPythonModule?.let { setModule(it) }
        isUseModuleSdk = true
        interpreterOptions = ""
        workingDirectory = ""
        setAddContentRoots(false)
        setAddSourceRoots(false)
    }

    public override fun getOptions(): RobotCodeRunConfigurationOptions {
        return super.getOptions() as RobotCodeRunConfigurationOptions
    }

    // fails with the IDE's run error before a process or a debug session starts, for the interpreter that the run uses
    override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState {
        val interpreter = pythonInterpreterOf(sdk)
        interpreterRefusal(interpreter)?.let { throw CantRunException(it) }
        project.robotCodeEnvironment.ensureUsableForRun(interpreter)
        return RobotCodeRunProfileState(this, environment)
    }

    // Only the first problem is reported, and only an error keeps the configuration from running, so errors come
    // first. Only results that exist are read, the result of the environment check and the cached profile list, so
    // that no process starts while the IDE waits.
    override fun checkConfiguration() {
        super<AbstractPythonRunConfiguration>.checkConfiguration()
        if (project.isDefault) {
            return
        }
        val problems = listOfNotNull(interpreterProblem(), targetProblem(), unknownProfilesProblem())
        (problems.firstOrNull { it is RuntimeConfigurationError } ?: problems.firstOrNull())?.let { throw it }
    }

    // PyCharm reports a configuration without an interpreter itself; without a result, the interpreter is checked in
    // the background
    private fun interpreterProblem(): RuntimeConfigurationException? {
        val interpreter = pythonInterpreterOf(sdk ?: return null)
        interpreterRefusal(interpreter)?.let { return RuntimeConfigurationError(it) }
        val environment = project.robotCodeEnvironment
        return when (val state = environment.state(interpreter)) {
            EnvironmentState.Unknown -> {
                environment.requestCheck(interpreter)
                null
            }

            // the Runnable fix, because the constructor with ConfigurationQuickFix is experimental
            is EnvironmentState.Checked -> if (state.isUsable) null else RuntimeConfigurationError(
                state.messageFor(environment.ownerOf(interpreter)),
                Runnable { RobotCodeConfigurePythonInterpreterAction.showPythonInterpreterSettings(project) }
            )

            is EnvironmentState.Failed ->
                RuntimeConfigurationWarning(state.messageFor(environment.ownerOf(interpreter)))
            EnvironmentState.Checking -> null
        }
    }

    // A path that does not exist stops the run in Robot Framework anyway. A stored item that the last discovery did
    // not find, for example after a rename, may still run, so it is a warning.
    private fun targetProblem(): RuntimeConfigurationException? {
        return when (options.targetKind) {
            RobotRunTargetKind.PATHS -> {
                // a macro that would ask the user is not expanded during the validation
                val configurator = ProgramParametersConfigurator().apply { setValidation(true) }
                val missing = missingTargetPaths(options.targetPaths, workingDirectoryPath()) {
                    try {
                        configurator.expandPathAndMacros(it, module, project)
                    } catch (_: IncorrectOperationException) {
                        null
                    }
                }
                missing.takeIf { it.isNotEmpty() }?.let {
                    RuntimeConfigurationError(RobotCodeBundle.message("run.target.paths.missing", quoted(it), it.size))
                }
            }

            RobotRunTargetKind.SELECTION -> {
                // discovery runs with the profiles of the project, and other profiles can find other items
                val projectProfiles = RobotCodePersonalConfiguration.getInstance(project).profiles.toList()
                if (resolveRunProfiles(options.profilesKind, options.profiles, projectProfiles) != projectProfiles) {
                    return null
                }
                val stale = staleSelectionItems(options.selection, project.testManger.testItems)
                stale.takeIf { it.isNotEmpty() }?.let {
                    RuntimeConfigurationWarning(
                        RobotCodeBundle.message("run.target.selection.stale", quoted(it), it.size)
                    )
                }
            }
        }
    }

    private fun unknownProfilesProblem(): RuntimeConfigurationException? {
        val unknown = unknownProfiles(options, project.profileListCache.cached)
        if (unknown.isEmpty()) {
            return null
        }
        return RuntimeConfigurationWarning(
            RobotCodeBundle.message("run.options.profiles.unknown", quoted(unknown), unknown.size)
        )
    }

    private fun quoted(names: List<String>): String = names.joinToString(", ") { "\"$it\"" }

    override fun createConfigurationEditor(): SettingsEditor<RobotCodeRunConfiguration> {
        return RobotCodeRunConfigurationEditor(this)
    }

    override fun isNewUiSupported(): Boolean = true

    private fun workingDirectoryPath(): Path? = try {
        Path.of(workingDirectorySafe)
    } catch (_: InvalidPathException) {
        null
    }

    // the name of a configuration created from context follows its target
    override fun suggestedName(): String? {
        return targetName(options, project.basePath?.substringAfterLast('/'), workingDirectoryPath())
    }

    // a renamed or moved file or folder of a "Files and folders" target: the target follows, and a generated name too
    override fun getRefactoringElementListener(element: PsiElement?): RefactoringElementListener? {
        if (options.targetKind != RobotRunTargetKind.PATHS) {
            return null
        }
        val oldPath = (element as? PsiFileSystemItem)?.virtualFile?.fileSystemPath() ?: return null
        val base = workingDirectoryPath()
        if (options.targetPaths.none { resolveStoredPath(it, base)?.startsWith(oldPath) == true }) {
            return null
        }
        return object : RefactoringElementListener {
            override fun elementMoved(newElement: PsiElement) = follow(newElement)

            override fun elementRenamed(newElement: PsiElement) = follow(newElement)

            private fun follow(newElement: PsiElement) {
                val newPath = (newElement as? PsiFileSystemItem)?.virtualFile?.fileSystemPath() ?: return
                val generated = isGeneratedName
                options.targetPaths = options.targetPaths.map { stored ->
                    val resolved = resolveStoredPath(stored, base)
                    if (resolved?.startsWith(oldPath) == true) {
                        pathRelativeTo(newPath.resolve(oldPath.relativize(resolved)), base)
                    } else {
                        stored
                    }
                }.toMutableList()
                if (generated) {
                    setGeneratedName()
                }
            }
        }
    }

    // Run and Debug use RobotCode's runners
    override fun canRunWithCoverage(): Boolean = false

    override fun canRunUnderDebug(): Boolean = false

    override fun createTestConsoleProperties(executor: Executor): SMTRunnerConsoleProperties {
        return RobotRunnerConsoleProperties(this, "Robot Framework", executor)
    }

    override fun readExternal(element: Element) {
        // PyCharm writes this field for every configuration; earlier versions of the plugin did not
        val earlierVersion = JDOMExternalizerUtil.readField(element, "ADD_CONTENT_ROOTS") == null
        super<AbstractPythonRunConfiguration>.readExternal(element)
        if (earlierVersion) {
            applyRobotCodeDefaults()
        }
    }
}

/**
 * The custom profiles of [options] that the profile [list] of `robot.toml` does not contain. Without a list, or with a
 * list that holds neither profiles nor messages and so could not be read, none are reported.
 */
internal fun unknownProfiles(options: RobotCodeRunConfigurationOptions, list: ProfileList?): List<String> {
    if (options.profilesKind != RobotRunProfilesKind.CUSTOM || list == null) {
        return listOf()
    }
    if (list.profiles.isEmpty() && list.messages.isEmpty()) {
        return listOf()
    }
    val known = list.profiles.map { it.name }.toSet()
    return options.profiles.map { it.trim() }.filter { it.isNotEmpty() && it !in known }
}

private fun com.intellij.openapi.vfs.VirtualFile.fileSystemPath(): Path? = try {
    toNioPath().normalize()
} catch (_: UnsupportedOperationException) {
    null
}
