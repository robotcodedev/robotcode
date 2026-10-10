package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.testframework.sm.runner.SMRunnerConsolePropertiesProvider
import com.intellij.execution.testframework.sm.runner.SMTRunnerConsoleProperties
import com.intellij.openapi.options.SettingsEditor
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.JDOMExternalizerUtil
import com.jetbrains.python.run.AbstractPythonRunConfiguration
import com.jetbrains.python.run.DebugAwareConfiguration
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import dev.robotcode.robotcode4ij.robotPythonModule
import org.jdom.Element

/**
 * A Robot Framework run configuration. It is a PyCharm Python run configuration, so it has PyCharm's interpreter,
 * environment and working-directory options, and stores what it runs, its target, in
 * [RobotCodeRunConfigurationOptions].
 */
class RobotCodeRunConfiguration(project: Project, factory: ConfigurationFactory) :
    AbstractPythonRunConfiguration<RobotCodeRunConfiguration>(project, factory), SMRunnerConsolePropertiesProvider,
    DebugAwareConfiguration {

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

    // fails with the IDE's run error before a process or a debug session starts
    override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState {
        project.robotCodeEnvironment.ensureUsableForRun()
        return RobotCodeRunProfileState(this, environment)
    }

    override fun createConfigurationEditor(): SettingsEditor<RobotCodeRunConfiguration> {
        return RobotCodeRunConfigurationEditor(this)
    }

    override fun isNewUiSupported(): Boolean = true

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
