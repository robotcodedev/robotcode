package dev.robotcode.robotcode4ij

import com.intellij.execution.CantRunException
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.openapi.application.PathManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.modules
import com.intellij.util.messages.Topic
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
import org.jetbrains.annotations.VisibleForTesting
import java.net.URI
import java.net.URL
import java.nio.file.Path
import java.util.concurrent.atomic.AtomicInteger
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

/** The module whose Python interpreter RobotCode uses: the first module that has one. */
val Project.robotPythonModule: com.intellij.openapi.module.Module?
    get() {
        return this.modules.firstOrNull { PythonSdkUtil.findPythonSdk(it) != null }
    }

val Project.robotPythonSdk: com.intellij.openapi.projectRoots.Sdk?
    get() {
        return robotPythonModule?.let { PythonSdkUtil.findPythonSdk(it) }
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

/**
 * Announces that RobotCode settings changed, applied on a settings page or loaded from the stored state; the restart
 * manager decides what the change needs.
 */
fun interface RobotCodeSettingsListener {
    fun settingsChanged()

    companion object {
        @Topic.ProjectLevel
        val TOPIC = Topic(RobotCodeSettingsListener::class.java, Topic.BroadcastDirection.NONE)
    }
}

fun Project.publishRobotCodeSettingsChanged() {
    messageBus.syncPublisher(RobotCodeSettingsListener.TOPIC).settingsChanged()
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
    
    // whether the pending restart also runs a full discovery
    @Volatile
    private var discoveryRequested = false
    
    // what the running server and the last full discovery got
    @Volatile
    private var serverSnapshot: ServerSnapshot? = null
    
    @Volatile
    private var discoverySnapshot: DiscoverySnapshot? = null
    
    @Volatile
    private var settingsJob: Job? = null
    
    val decisions = AtomicInteger()
    
    // The restart waits for the check and starts the server itself.
    private suspend fun restart(reset: Boolean, discovery: Boolean) {
        val environment = project.robotCodeEnvironment
        if (reset) {
            environment.checkAgain().await()
        } else {
            environment.awaitRunningCheck()
        }
        project.langServerManager.restart()
        if (discovery) {
            project.testManger.refreshDebounced()
        }
    }
    
    @Synchronized
    fun restartDebounced(reset: Boolean = false, discovery: Boolean = true) {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        
        // a restart that a newer one replaces passes on its request for a discovery
        val runDiscovery = discovery || (refreshJob?.isActive == true && discoveryRequested)
        refreshJob?.cancel()
        discoveryRequested = runDiscovery
        project.langServerManager.restartPending = true
        
        // a restart that a newer one replaced leaves the pending state to the newer one
        val job = scope.launch(restartDispatcher, start = CoroutineStart.LAZY) {
            try {
                delay(DEBOUNCE_DELAY)
                if (project.isOpen && !project.isDisposed) {
                    restart(reset, runDiscovery)
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
    
    fun serverStarted(snapshot: ServerSnapshot?) {
        serverSnapshot = snapshot
    }
    
    fun discoveryRan(snapshot: DiscoverySnapshot) {
        discoverySnapshot = snapshot
    }
    
    @Synchronized
    fun settingsChanged() {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        settingsJob?.cancel()
        settingsJob = scope.launch(restartDispatcher) {
            delay(DEBOUNCE_DELAY)
            decide()
        }
    }
    
    // Without a usable interpreter the environment check starts the server and discovery once it is usable, and with
    // "Disable extension" the switch does.
    private suspend fun decide() {
        decisions.incrementAndGet()
        val environment = project.robotCodeEnvironment
        environment.awaitRunningCheck()
        if (project.isRobotCodeDisabled || !environment.projectState.isUsable) {
            return
        }
        val work = decideRestart(serverSnapshot, project.serverSnapshot(), discoverySnapshot, project.discoverySnapshot())
        // the restart path joins this restart with one that a configuration file requested
        if (work.server) {
            restartDebounced(discovery = work.discovery)
        } else if (work.discovery) {
            project.testManger.refreshDebounced()
        }
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

/**
 * Restarts the language server alone, debounced like [restartAll].
 */
fun Project.restartLanguageServer() {
    if (isDefault || isRobotCodeDisabled) {
        return
    }
    this.service<RobotCodeRestartManager>().restartDebounced(discovery = false)
}

internal fun Project.recordServerSnapshot() {
    this.service<RobotCodeRestartManager>().serverStarted(serverSnapshot())
}

internal fun Project.recordDiscoverySnapshot(commandLine: GeneralCommandLine) {
    this.service<RobotCodeRestartManager>().discoveryRan(DiscoverySnapshot(commandLine))
}

/** The number of decisions that settings changes led to. */
internal val Project.restartDecisions: Int
    @VisibleForTesting get() = this.service<RobotCodeRestartManager>().decisions.get()

/**
 * Passes changes of the RobotCode settings to the restart manager.
 */
class RobotCodeSettingsRestartListener(private val project: Project) : RobotCodeSettingsListener {
    override fun settingsChanged() {
        if (!project.isDefault) {
            project.service<RobotCodeRestartManager>().settingsChanged()
        }
    }
}
