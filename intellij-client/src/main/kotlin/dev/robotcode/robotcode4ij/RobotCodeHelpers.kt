package dev.robotcode.robotcode4ij

import com.intellij.execution.CantRunException
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.openapi.application.PathManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.modules
import com.jetbrains.python.sdk.PythonSdkUtil
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.lsp.langServerManager
import dev.robotcode.robotcode4ij.testing.testManger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.net.URI
import java.net.URL
import java.nio.file.Path
import kotlin.io.path.pathString

class RobotCodeHelpers {
    companion object {
        val basePath: Path = robotCodeBasePath(
            pluginPathOf(RobotCodeHelpers::class.java.getResource("RobotCodeHelpers.class"))
        )
        val bundledPath: Path = basePath.resolve("bundled")
        val toolPath: Path = bundledPath.resolve("tool")
        val robotCodePath: Path = toolPath.resolve("robotcode")
    }
}

/**
 * The folder with the plugin's bundled files, below the directory from which the IDE loaded the plugin.
 */
internal fun robotCodeBasePath(pluginPath: Path?): Path {
    return (pluginPath ?: PathManager.getPluginsDir().resolve("robotcode4ij")).resolve("data")
}

/**
 * The directory of the plugin whose jar in `lib` holds [classResource], or null when the class does not come from a jar.
 * The platform's lookups of a plugin's descriptor are internal API.
 */
internal fun pluginPathOf(classResource: URL?): Path? {
    if (classResource?.protocol != "jar") {
        return null
    }
    val jar = Path.of(URI(classResource.path.substringBefore("!/")))
    return jar.parent?.parent
}

val Project.robotPythonSdk: com.intellij.openapi.projectRoots.Sdk?
    get() {
        return this.modules.firstNotNullOfOrNull { PythonSdkUtil.findPythonSdk(it) }
    }

/**
 * The arguments after the `robotcode` entry point. The extra arguments come first, so that the plugin's own options win
 * when the extra arguments set the same option; `-p` collects, so profiles among them add to [profiles].
 */
internal fun robotCodeArguments(
    extraArgs: List<String>,
    format: String,
    noColor: Boolean,
    noPager: Boolean,
    profiles: List<String>,
    args: List<String>
): List<String> {
    return buildList {
        addAll(extraArgs)
        if (format.isNotEmpty()) addAll(listOf("--format", format))
        if (noColor) add("--no-color")
        if (noPager) add("--no-pager")
        profiles.forEach { addAll(listOf("-p", it)) }
        addAll(args)
    }
}

/**
 * The command line of a `robotcode` command. It throws [CantRunException] with the text of the result when the project's
 * interpreter is not usable.
 */
fun Project.buildRobotCodeCommandLine(
    args: Array<String> = arrayOf(),
    profiles: Array<String> = RobotCodePersonalConfiguration.getInstance(this).profiles.toTypedArray(),
    extraArgs: Array<String> = RobotCodePersonalConfiguration.getInstance(this).extraArgsList.toTypedArray(),
    format: String = "",
    noColor: Boolean = true,
    noPager: Boolean = true
): GeneralCommandLine {
    val interpreter = robotCodeEnvironment.projectInterpreter
    val state = robotCodeEnvironment.state(interpreter)
    if (!state.isUsable) {
        throw CantRunException(state.message)
    }
    
    val commandLine = GeneralCommandLine(
        interpreter.homePath,
        "-u",
        "-X",
        "utf8",
        RobotCodeHelpers.robotCodePath.pathString,
        *robotCodeArguments(
            extraArgs.toList(), format, noColor, noPager, profiles.toList(), args.toList()
        ).toTypedArray()
    ).withWorkDirectory(this.basePath).withCharset(Charsets.UTF_8)

    return commandLine
}

// The platform cancels the scope when the project closes or the plugin is unloaded.
@Service(Service.Level.PROJECT)
private class RobotCodeRestartManager(private val project: Project, private val scope: CoroutineScope) {
    companion object {
        private const val DEBOUNCE_DELAY = 500L
    }
    
    // one restart at a time, in the order they were requested
    @OptIn(ExperimentalCoroutinesApi::class)
    private val restartDispatcher = Dispatchers.IO.limitedParallelism(1)
    
    @Volatile
    private var refreshJob: Job? = null
    
    // The restart waits for the check and starts the server itself.
    private suspend fun restart(reset: Boolean = false) {
        val environment = project.robotCodeEnvironment
        if (reset) {
            environment.checkAgain().await()
        } else {
            environment.awaitRunningCheck()
        }
        project.langServerManager.restart()
        project.testManger.refreshDebounced()
    }
    
    fun restartDebounced(reset: Boolean = false) {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        
        refreshJob?.cancel()
        project.langServerManager.restartPending = true
        
        // a restart that a newer one replaced leaves the pending state to the newer one
        val job = scope.launch(restartDispatcher, start = CoroutineStart.LAZY) {
            try {
                delay(DEBOUNCE_DELAY)
                if (project.isOpen && !project.isDisposed) {
                    restart(reset)
                }
            } finally {
                if (refreshJob === coroutineContext[Job]) {
                    refreshJob = null
                    // the scope also ends when the project closes
                    if (!project.isDisposed) {
                        project.langServerManager.restartPending = false
                    }
                }
            }
        }
        refreshJob = job
        job.start()
    }
}

fun Project.restartAll(reset: Boolean = false) {
    // settings for new projects start nothing, and neither does a project with "Disable extension"
    if (isDefault || isRobotCodeDisabled) {
        return
    }
    // the restart actions also undo a disable in the Language Servers tool window
    if (reset) {
        langServerManager.enableForSession()
    }
    this.service<RobotCodeRestartManager>().restartDebounced(reset)
}
