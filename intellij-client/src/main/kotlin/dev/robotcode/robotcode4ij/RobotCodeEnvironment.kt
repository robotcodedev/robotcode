package dev.robotcode.robotcode4ij

import com.intellij.execution.CantRunException
import com.intellij.execution.ExecutionException
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.CapturingProcessHandler
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.progress.runBlockingCancellable
import com.intellij.openapi.project.Project
import com.intellij.openapi.projectRoots.Sdk
import com.intellij.platform.backend.workspace.workspaceModel
import com.intellij.platform.ide.progress.runWithModalProgressBlocking
import com.intellij.platform.workspace.jps.entities.SdkEntity
import com.intellij.platform.workspace.storage.EntityChange
import com.intellij.util.messages.Topic
import com.jetbrains.python.sdk.PythonSdkUtil
import dev.robotcode.robotcode4ij.lsp.langServerManager
import dev.robotcode.robotcode4ij.testing.testManger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.jetbrains.annotations.TestOnly
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.io.path.Path
import kotlin.io.path.exists

/**
 * What the check found out about an interpreter.
 */
sealed class EnvironmentResult {
    /** The text for the user, or null when the interpreter is usable. */
    abstract val message: String?

    data object Usable : EnvironmentResult() {
        override val message: String? = null
    }

    data object NoInterpreter : EnvironmentResult() {
        override val message get() = RobotCodeBundle.message("python.noInterpreter")
    }

    data class PathNotFound(val path: String) : EnvironmentResult() {
        override val message get() = RobotCodeBundle.message("python.interpreterNotFound", path)
    }

    data class PythonTooOld(val version: String) : EnvironmentResult() {
        override val message get() = RobotCodeBundle.message("python.tooOld", version)
    }

    data object RobotNotInstalled : EnvironmentResult() {
        override val message get() = RobotCodeBundle.message("python.noRobotFramework")
    }

    data class RobotTooOld(val version: String) : EnvironmentResult() {
        override val message get() = RobotCodeBundle.message("python.robotTooOld", version)
    }

    data object Remote : EnvironmentResult() {
        override val message get() = RobotCodeBundle.message("python.remote")
    }
}

/**
 * The state of the check of one interpreter.
 */
sealed class EnvironmentState {
    data object Unknown : EnvironmentState()
    data object Checking : EnvironmentState()
    data class Checked(val result: EnvironmentResult) : EnvironmentState()

    /** The check itself failed, so nothing is known about the interpreter. */
    data class Failed(val reason: String) : EnvironmentState()

    val isUsable: Boolean
        get() = this is Checked && result == EnvironmentResult.Usable

    val message: String
        get() = when (this) {
            is Checked -> result.message ?: ""
            is Failed -> RobotCodeBundle.message("python.checkFailed", reason)
            else -> RobotCodeBundle.message("python.checking")
        }
}

enum class InterpreterKind { NONE, LOCAL, REMOTE }

/**
 * An interpreter, identified by its kind, the name of its SDK and its home path.
 */
data class PythonInterpreter(val kind: InterpreterKind, val sdkName: String?, val homePath: String?)

fun pythonInterpreterOf(sdk: Sdk?): PythonInterpreter {
    return when {
        sdk == null -> PythonInterpreter(InterpreterKind.NONE, null, null)
        PythonSdkUtil.isRemote(sdk) -> PythonInterpreter(InterpreterKind.REMOTE, sdk.name, sdk.homePath)
        else -> PythonInterpreter(InterpreterKind.LOCAL, sdk.name, sdk.homePath)
    }
}

/**
 * The result that is known without running the interpreter, or null when the interpreter has to be probed.
 */
internal fun classifyInterpreter(interpreter: PythonInterpreter): EnvironmentResult? {
    return when (interpreter.kind) {
        InterpreterKind.NONE -> EnvironmentResult.NoInterpreter
        // its path is a path on another machine
        InterpreterKind.REMOTE -> EnvironmentResult.Remote
        InterpreterKind.LOCAL -> {
            val path = interpreter.homePath
            if (path == null || !Path(path).exists()) EnvironmentResult.PathNotFound(path ?: "") else null
        }
    }
}

/**
 * The states of the interpreters and their checks: at most one check per interpreter runs at a time, on [scope].
 * [onChange] gets every change of a state.
 */
internal class EnvironmentChecks(
    private val scope: CoroutineScope,
    private val check: suspend (PythonInterpreter) -> EnvironmentState,
    private val onChange: (PythonInterpreter, EnvironmentState) -> Unit
) {
    private class RunningCheck {
        val result = CompletableDeferred<EnvironmentState>()
        lateinit var job: Job

        // set when a new check was requested while this one ran
        var again = false
    }

    private val lock = Any()
    private val states = HashMap<PythonInterpreter, EnvironmentState>()
    private val running = HashMap<PythonInterpreter, RunningCheck>()

    fun state(interpreter: PythonInterpreter): EnvironmentState {
        return synchronized(lock) { states[interpreter] ?: EnvironmentState.Unknown }
    }

    /** Starts a check when the interpreter has not been checked yet. */
    fun request(interpreter: PythonInterpreter) {
        synchronized(lock) {
            if (interpreter !in states) start(interpreter) else null
        }?.let { begin(interpreter, it) }
    }

    /** Starts a new check; a check that is running is followed by a new one, whose result counts. */
    fun reset(interpreter: PythonInterpreter): Deferred<EnvironmentState> {
        var started = false
        val check = synchronized(lock) {
            running[interpreter]?.also { it.again = true } ?: start(interpreter).also { started = true }
        }
        if (started) begin(interpreter, check)
        return check.result
    }

    /** The result of the running check, or null when no check runs. */
    fun running(interpreter: PythonInterpreter): Deferred<EnvironmentState>? {
        return synchronized(lock) { running[interpreter]?.result }
    }

    @TestOnly
    internal fun setState(interpreter: PythonInterpreter, state: EnvironmentState?) {
        synchronized(lock) {
            if (state == null) states.remove(interpreter) else states[interpreter] = state
        }
    }

    @TestOnly
    internal fun clear() {
        synchronized(lock) {
            states.clear()
        }
    }

    private fun start(interpreter: PythonInterpreter): RunningCheck {
        val check = RunningCheck()
        running[interpreter] = check
        states[interpreter] = EnvironmentState.Checking
        // starts after Checking is published, so that the result is published after it
        check.job = scope.launch(start = CoroutineStart.LAZY) {
            try {
                while (true) {
                    val state = try {
                        check(interpreter)
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Exception) {
                        EnvironmentState.Failed(e.message ?: e.javaClass.simpleName)
                    }
                    val done = synchronized(lock) {
                        if (check.again) {
                            check.again = false
                            false
                        } else {
                            running.remove(interpreter)
                            states[interpreter] = state
                            true
                        }
                    }
                    if (done) {
                        onChange(interpreter, state)
                        check.result.complete(state)
                        return@launch
                    }
                }
            } finally {
                // a check that ended without a result, for example with the project, leaves no state behind
                if (!check.result.isCompleted) {
                    synchronized(lock) {
                        if (running[interpreter] === check) {
                            running.remove(interpreter)
                            states.remove(interpreter)
                        }
                    }
                    check.result.cancel()
                }
            }
        }
        return check
    }

    private fun begin(interpreter: PythonInterpreter, check: RunningCheck) {
        onChange(interpreter, EnvironmentState.Checking)
        check.job.start()
    }
}

/**
 * Gets every change of the state of an interpreter's check.
 */
fun interface RobotCodeEnvironmentListener {
    fun stateChanged(interpreter: PythonInterpreter, state: EnvironmentState)
}

/**
 * Owns the state of the environment check. Consumers read the state and do not wait for it.
 */
@Service(Service.Level.PROJECT)
class RobotCodeEnvironment(private val project: Project, private val scope: CoroutineScope) {
    companion object {
        @Topic.ProjectLevel
        val TOPIC = Topic(RobotCodeEnvironmentListener::class.java, Topic.BroadcastDirection.NONE)

        const val PROBE_TIMEOUT_MILLIS = 30_000
    }

    internal val checks = EnvironmentChecks(scope, ::runCheck) { interpreter, state ->
        if (!project.isDisposed) {
            project.messageBus.syncPublisher(TOPIC).stateChanged(interpreter, state)
        }
    }

    /** Set once the project is known to use Robot Framework, when it has Robot Framework files or one was opened. */
    @Volatile
    var isRobotProject = false
        private set

    @Volatile
    private var lastInterpreter: PythonInterpreter? = null

    private val watching = AtomicBoolean(false)

    @TestOnly
    internal fun resetForTests() {
        checks.clear()
        isRobotProject = false
        lastInterpreter = projectInterpreter
    }

    val projectInterpreter: PythonInterpreter
        get() = pythonInterpreterOf(project.robotPythonSdk)

    val projectState: EnvironmentState
        get() = checks.state(projectInterpreter)

    fun state(interpreter: PythonInterpreter): EnvironmentState = checks.state(interpreter)

    fun requestCheck(interpreter: PythonInterpreter = projectInterpreter) = checks.request(interpreter)

    /** Checks the interpreter again, for example on Restart. */
    fun checkAgain(interpreter: PythonInterpreter = projectInterpreter): Deferred<EnvironmentState> {
        return checks.reset(interpreter)
    }

    /** Waits for the result of a running check of the interpreter, and returns at once when none runs. */
    suspend fun awaitRunningCheck(interpreter: PythonInterpreter = projectInterpreter) {
        checks.running(interpreter)?.await()
    }

    /**
     * Throws [CantRunException] with the text of the result unless the project's interpreter is usable. Without a
     * result, or after a failed check, it checks first, with a progress dialog that can be cancelled on the EDT.
     */
    fun ensureUsableForRun() {
        val interpreter = projectInterpreter
        var state = checks.state(interpreter)
        if (state !is EnvironmentState.Checked) {
            state = try {
                if (ApplicationManager.getApplication().isDispatchThread) {
                    runWithModalProgressBlocking(project, RobotCodeBundle.message("python.check.progress")) {
                        resultForRun(interpreter)
                    }
                } else {
                    runBlockingCancellable { resultForRun(interpreter) }
                }
            } catch (_: CancellationException) {
                throw CantRunException(RobotCodeBundle.message("python.check.cancelled"))
            }
        }
        if (!state.isUsable) {
            throw CantRunException(state.message)
        }
    }

    private suspend fun resultForRun(interpreter: PythonInterpreter): EnvironmentState {
        return when (checks.state(interpreter)) {
            is EnvironmentState.Checked -> checks.state(interpreter)
            is EnvironmentState.Failed -> checks.reset(interpreter).await()
            else -> {
                checks.request(interpreter)
                checks.running(interpreter)?.await() ?: checks.state(interpreter)
            }
        }
    }

    /**
     * Marks the project as a Robot Framework project. Without a result the interpreter is checked; with a usable
     * result the first discovery runs, and LSP4IJ starts the server for the file that is opened.
     */
    fun markRobotProject() {
        if (isRobotProject) {
            return
        }
        isRobotProject = true
        val interpreter = projectInterpreter
        when {
            checks.state(interpreter) == EnvironmentState.Unknown -> checks.request(interpreter)
            checks.state(interpreter).isUsable -> project.testManger.refreshDebounced()
        }
    }

    /**
     * Follows the changes of the workspace model: a new project interpreter is checked and restarts the server in a Robot
     * Framework project; an SDK change of an interpreter that is not usable checks it again.
     */
    fun watchWorkspaceModel() {
        if (!watching.compareAndSet(false, true)) {
            return
        }
        lastInterpreter = projectInterpreter
        scope.launch {
            project.workspaceModel.eventLog.collect { event ->
                workspaceChanged(event.getChanges(SdkEntity::class.java))
            }
        }
    }

    internal fun workspaceChanged(sdkChanges: List<EntityChange<SdkEntity>>) {
        val interpreter = projectInterpreter
        if (interpreter != lastInterpreter) {
            lastInterpreter = interpreter
            // The restart waits for the check; it also starts a server whose start failed with the last interpreter.
            // It is requested first, so that the result of the check does not start the server a second time.
            if (isRobotProject || project.langServerManager.isRunning) {
                project.restartAll()
            }
            if (isRobotProject) {
                checks.reset(interpreter)
            }
            return
        }

        val state = checks.state(interpreter)
        val sdkChanged = sdkChanges.any { (it.oldEntity ?: it.newEntity)?.name == interpreter.sdkName }
        if (sdkChanged && (state is EnvironmentState.Failed || (state is EnvironmentState.Checked && !state.isUsable))) {
            checks.reset(interpreter)
        }
    }

    private suspend fun runCheck(interpreter: PythonInterpreter): EnvironmentState {
        classifyInterpreter(interpreter)?.let { return EnvironmentState.Checked(it) }

        val commandLine = GeneralCommandLine(interpreter.homePath!!, "-u", "-X", "utf8", "-c", PROBE_SNIPPET)
            .withCharset(Charsets.UTF_8)
        val output = try {
            withContext(Dispatchers.IO) {
                CapturingProcessHandler(commandLine).runProcess(PROBE_TIMEOUT_MILLIS, true)
            }
        } catch (e: ExecutionException) {
            thisLogger().warn("The check of the Python interpreter could not start: ${commandLine.commandLineString}", e)
            return EnvironmentState.Failed(RobotCodeBundle.message("python.check.notStarted"))
        }

        val state = probeState(output)
        if (state is EnvironmentState.Failed) {
            thisLogger().warn(
                "The check of the Python interpreter failed: ${commandLine.commandLineString}\n" +
                    "exit code: ${output.exitCode}, timeout: ${output.isTimeout}\n" +
                    "stdout: ${output.stdout}\nstderr: ${output.stderr}"
            )
        } else {
            thisLogger().info("Checked the Python interpreter ${interpreter.homePath}: $state")
        }
        return state
    }
}

val Project.robotCodeEnvironment: RobotCodeEnvironment
    get() = this.service<RobotCodeEnvironment>()
