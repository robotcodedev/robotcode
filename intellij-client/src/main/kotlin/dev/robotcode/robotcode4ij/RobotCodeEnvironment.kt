package dev.robotcode.robotcode4ij

import com.intellij.execution.CantRunException
import com.intellij.execution.ExecutionException
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.CapturingProcessHandler
import com.intellij.notification.Notification
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.smartReadAction
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.module.Module
import com.intellij.openapi.module.ModuleManager
import com.intellij.openapi.progress.runBlockingCancellable
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.modules
import com.intellij.openapi.projectRoots.Sdk
import com.intellij.platform.backend.workspace.workspaceModel
import com.intellij.platform.ide.progress.runWithModalProgressBlocking
import com.intellij.platform.workspace.jps.entities.ContentRootEntity
import com.intellij.platform.workspace.jps.entities.ModuleEntity
import com.intellij.platform.workspace.jps.entities.SdkEntity
import com.intellij.platform.workspace.storage.EntityChange
import com.intellij.util.messages.Topic
import com.jetbrains.python.sdk.PythonSdkUtil
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.editor.updateRobotCodeStatusBar
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
import org.jetbrains.annotations.PropertyKey
import org.jetbrains.annotations.TestOnly
import org.jetbrains.annotations.VisibleForTesting
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlin.io.path.Path
import kotlin.io.path.exists

/** Whose interpreter a check is about, which its texts name. */
enum class InterpreterOwner { PROJECT, RUN_CONFIGURATION }

/** The text of [projectKey] for the interpreter of the project, else the text of [runKey]. */
private fun ownerMessage(
    owner: InterpreterOwner,
    @PropertyKey(resourceBundle = "messages.RobotCode") projectKey: String,
    @PropertyKey(resourceBundle = "messages.RobotCode") runKey: String,
    vararg params: Any
): String = RobotCodeBundle.message(if (owner == InterpreterOwner.PROJECT) projectKey else runKey, *params)

/**
 * What the check found out about an interpreter, or, for the project, that the module whose interpreter RobotCode uses
 * is not chosen yet.
 */
sealed class EnvironmentResult {
    /** The text for the user about the interpreter of the project, or null when it is usable. */
    val message: String? get() = messageFor(InterpreterOwner.PROJECT)

    /** The text for the user about the interpreter of [owner], or null when it is usable. */
    abstract fun messageFor(owner: InterpreterOwner): String?

    data object Usable : EnvironmentResult() {
        override fun messageFor(owner: InterpreterOwner): String? = null
    }

    data object NoInterpreter : EnvironmentResult() {
        override fun messageFor(owner: InterpreterOwner) =
            ownerMessage(owner, "python.noInterpreter", "run.python.noInterpreter")
    }

    data class PathNotFound(val path: String) : EnvironmentResult() {
        override fun messageFor(owner: InterpreterOwner) =
            ownerMessage(owner, "python.interpreterNotFound", "run.python.interpreterNotFound", path)
    }

    data class PythonTooOld(val version: String) : EnvironmentResult() {
        override fun messageFor(owner: InterpreterOwner) =
            ownerMessage(owner, "python.tooOld", "run.python.tooOld", version)
    }

    data object RobotNotInstalled : EnvironmentResult() {
        override fun messageFor(owner: InterpreterOwner) =
            ownerMessage(owner, "python.noRobotFramework", "run.python.noRobotFramework")
    }

    data class RobotTooOld(val version: String) : EnvironmentResult() {
        override fun messageFor(owner: InterpreterOwner) =
            ownerMessage(owner, "python.robotTooOld", "run.python.robotTooOld", version)
    }

    // a run refuses a remote interpreter before it is checked, with a text of its own
    data object Remote : EnvironmentResult() {
        override fun messageFor(owner: InterpreterOwner) = RobotCodeBundle.message("python.remote")
    }

    /** Several modules are Robot Framework projects, and the user has not chosen one of [candidates] yet. */
    data class ModuleNotChosen(val candidates: List<String>) : EnvironmentResult() {
        override fun messageFor(owner: InterpreterOwner) =
            RobotCodeBundle.message("python.moduleNotChosen", candidates.joinToString(", "))
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

    /** The text for the user about the interpreter of the project. */
    val message: String
        get() = messageFor(InterpreterOwner.PROJECT)

    /**
     * The text for the user about the interpreter of [owner]. A run waits for the check of its interpreter, so only the
     * project's interpreter is still being checked when its text is shown.
     */
    fun messageFor(owner: InterpreterOwner): String = when (this) {
        is Checked -> result.messageFor(owner) ?: ""
        is Failed -> ownerMessage(owner, "python.checkFailed", "run.python.checkFailed", reason)
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

    /** The interpreters whose last check found them not usable or failed. */
    fun notUsable(): List<PythonInterpreter> {
        return synchronized(lock) {
            states.filter { (_, state) ->
                state is EnvironmentState.Failed || (state is EnvironmentState.Checked && !state.isUsable)
            }.keys.toList()
        }
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

    // the Robot Framework projects among the modules with an interpreter, as the last detection found them
    private data class ModuleDetection(val modules: List<String>, val robotModules: List<String>)

    @Volatile
    private var detection: ModuleDetection? = null

    private val choiceLock = Any()

    // the running detection, the modules it runs for, and whether it is to run once more
    private var detectionJob: Job? = null
    private var detectionModules: List<String>? = null
    private var detectionAgain = false
    private val detectionsStarted = AtomicInteger()

    /** The number of detections that were started. */
    internal val moduleDetections: Int
        @VisibleForTesting get() = detectionsStarted.get()

    // the choice that was logged and followed last, and the request to choose while it is shown
    private var lastChoice: ModuleChoice? = null
    private var choiceNotification: Notification? = null

    // without [interpreterKnown], as before the startup activity watches the workspace model
    @TestOnly
    internal fun resetForTests(interpreterKnown: Boolean = true) {
        checks.clear()
        isRobotProject = false
        synchronized(choiceLock) {
            detectionJob?.cancel()
            detectionJob = null
            detectionModules = null
            detectionAgain = false
            detection = null
            lastChoice = null
        }
        expireModuleChoiceNotification()
        lastInterpreter = if (interpreterKnown) projectInterpreter else null
    }

    // the choice of the module with the module and its interpreter, all from one resolution
    private class ProjectChoice(
        val resolution: ModuleResolution,
        val module: Module?,
        val interpreter: PythonInterpreter
    )

    private fun projectChoice(): ProjectChoice {
        val resolution = moduleResolution
        val module = (resolution.choice as? ModuleChoice.Resolved)?.moduleName?.let {
            ModuleManager.getInstance(project).findModuleByName(it)
        }
        return ProjectChoice(resolution, module, pythonInterpreterOf(module?.let { PythonSdkUtil.findPythonSdk(it) }))
    }

    // While the module is not chosen, the state is Checking during the detection and asks for the choice while
    // several modules are Robot Framework projects.
    private fun stateOf(current: ProjectChoice): EnvironmentState {
        return when (val choice = current.resolution.choice) {
            ModuleChoice.Detecting -> EnvironmentState.Checking
            is ModuleChoice.Waiting -> EnvironmentState.Checked(EnvironmentResult.ModuleNotChosen(choice.candidates))
            is ModuleChoice.Resolved -> checks.state(current.interpreter)
        }
    }

    val projectInterpreter: PythonInterpreter
        get() = projectChoice().interpreter

    /** The project, when [interpreter] is the interpreter of the chosen module, else the run configuration. */
    fun ownerOf(interpreter: PythonInterpreter): InterpreterOwner {
        val current = projectChoice()
        return if (current.resolution.choice is ModuleChoice.Resolved && current.interpreter == interpreter) {
            InterpreterOwner.PROJECT
        } else {
            InterpreterOwner.RUN_CONFIGURATION
        }
    }

    /** The state of the project's interpreter, see [projectInterpreterAndState]. */
    val projectState: EnvironmentState
        get() = stateOf(projectChoice())

    /**
     * The project's interpreter and its state, from the same choice of the module. While the module is not chosen,
     * the state is [EnvironmentState.Checking] during the detection and asks for the choice while several modules are
     * Robot Framework projects.
     */
    val projectInterpreterAndState: Pair<PythonInterpreter, EnvironmentState>
        get() = projectChoice().let { it.interpreter to stateOf(it) }

    // the modules that have a Python interpreter, their own or the project's, in the order of the project
    private fun pythonModules(): List<Module> = project.modules.filter { PythonSdkUtil.findPythonSdk(it) != null }

    /** The names of the modules that have a Python interpreter, among which the user can choose. */
    val pythonModuleNames: List<String>
        get() = pythonModules().map { it.name }

    /**
     * The choice of the module, from the modules and the stored choice as they are now. A detection that the choice
     * needs is started, and the choice is [ModuleChoice.Detecting] until its result is there.
     */
    internal val moduleResolution: ModuleResolution
        get() {
            val modules = pythonModules().map { it.name }
            val chosen = RobotCodePersonalConfiguration.getInstance(project).pythonModule
            val resolution = resolveModuleChoice(
                modules, chosen, detection?.takeIf { it.modules == modules }?.robotModules
            )
            if (resolution.choice == ModuleChoice.Detecting) {
                detectModules(modules, again = false)
            }
            return resolution
        }

    val moduleChoice: ModuleChoice
        get() = moduleResolution.choice

    /** The module whose interpreter RobotCode uses, or null while the choice is missing or no module has one. */
    val pythonModule: Module?
        get() = projectChoice().module

    fun state(interpreter: PythonInterpreter): EnvironmentState = checks.state(interpreter)

    fun requestCheck(interpreter: PythonInterpreter = projectInterpreter) = checks.request(interpreter)

    /** Checks the interpreter again, for example on Restart. */
    fun checkAgain(interpreter: PythonInterpreter = projectInterpreter): Deferred<EnvironmentState> {
        return checks.reset(interpreter)
    }

    /**
     * Checks every interpreter again whose last result is not usable, also the interpreters of run configurations,
     * for example on Retry and Restart.
     */
    fun checkAgainNotUsable() {
        checks.notUsable().forEach { checks.reset(it) }
    }

    /** Waits for the result of a running check of the interpreter, and returns at once when none runs. */
    suspend fun awaitRunningCheck(interpreter: PythonInterpreter = projectInterpreter) {
        checks.running(interpreter)?.await()
    }

    /**
     * Throws [CantRunException] with the text of the result unless [interpreter] is usable, or without one the
     * project's interpreter. Without a result, or after a failed check, it checks first, with a progress dialog that
     * can be cancelled on the EDT. While the project's module is not chosen, there is nothing to check, and it says so.
     * The texts name the run configuration when [interpreter] is not the project's, see [ownerOf].
     */
    fun ensureUsableForRun(interpreter: PythonInterpreter? = null) {
        val checked = interpreter ?: projectChoice().let { current ->
            if (current.resolution.choice !is ModuleChoice.Resolved) {
                throw CantRunException(stateOf(current).message)
            }
            current.interpreter
        }
        val owner = if (interpreter == null) InterpreterOwner.PROJECT else ownerOf(interpreter)
        var state = checks.state(checked)
        if (state !is EnvironmentState.Checked) {
            state = try {
                if (ApplicationManager.getApplication().isDispatchThread) {
                    val title = ownerMessage(owner, "python.check.progress", "run.python.check.progress")
                    runWithModalProgressBlocking(project, title) {
                        resultForRun(checked)
                    }
                } else {
                    runBlockingCancellable { resultForRun(checked) }
                }
            } catch (_: CancellationException) {
                throw CantRunException(ownerMessage(owner, "python.check.cancelled", "run.python.check.cancelled"))
            }
        }
        if (!state.isUsable) {
            throw CantRunException(state.messageFor(owner))
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
        project.updateRobotCodeStatusBar()
        // like VS Code, which activates RobotCode only in workspaces with Robot Framework files
        project.announceNewVersion()
        val (interpreter, state) = projectInterpreterAndState
        when {
            state == EnvironmentState.Unknown -> requestCheck(interpreter)
            state.isUsable -> project.testManger.refreshDebounced()
        }
    }

    /**
     * Starts RobotCode as when the project is opened, for example when "Disable extension" is unchecked: without a
     * result the interpreter is checked, and a usable result starts the server and a full discovery.
     */
    fun startAgain() {
        if (!isRobotProject) {
            return
        }
        val (interpreter, state) = projectInterpreterAndState
        when {
            state == EnvironmentState.Unknown -> requestCheck(interpreter)
            state.isUsable -> {
                project.langServerManager.start()
                project.testManger.refreshDebounced()
            }
        }
    }

    /**
     * Follows the changes of the workspace model: the module is chosen again, a new project interpreter is checked and
     * restarts the server in a Robot Framework project, and an SDK change of an interpreter that is not usable checks
     * it again.
     */
    fun watchWorkspaceModel() {
        if (!watching.compareAndSet(false, true)) {
            return
        }
        noteModuleChoice()
        lastInterpreter = projectInterpreter
        scope.launch {
            project.workspaceModel.eventLog.collect { event ->
                val modulesChanged = event.getChanges(ModuleEntity::class.java).isNotEmpty() ||
                    event.getChanges(ContentRootEntity::class.java).isNotEmpty()
                workspaceChanged(event.getChanges(SdkEntity::class.java), modulesChanged)
            }
        }
    }

    internal fun workspaceChanged(sdkChanges: List<EntityChange<SdkEntity>>, modulesChanged: Boolean) {
        // the detection reads the files of the modules' content roots
        if (modulesChanged) {
            redetectModules()
        }
        val choiceChanged = noteModuleChoice()
        val interpreterChanged = followProjectInterpreter()
        if (choiceChanged && !interpreterChanged) {
            publishProjectState()
        }

        // an interpreter that is not usable, the project's or a run configuration's, is checked again when its SDK
        // changes; a new project interpreter is checked already
        val changedSdks = sdkChanges.mapNotNullTo(HashSet()) { (it.oldEntity ?: it.newEntity)?.name }
        checks.notUsable().filter { it.sdkName in changedSdks }.forEach { checks.reset(it) }
    }

    /**
     * Follows a change of the settings, which can hold another choice of the module, as [workspaceChanged] follows the
     * workspace model.
     */
    fun settingsChanged() {
        scope.launch {
            if (noteModuleChoice() && !followProjectInterpreter()) {
                publishProjectState()
            }
        }
    }

    /** Removes the request to choose a module. */
    fun expireModuleChoiceNotification() {
        synchronized(choiceLock) { choiceNotification.also { choiceNotification = null } }?.expire()
    }

    /**
     * Follows a change of "Disable extension": switched off, the request to choose disappears; switched on while the
     * choice waits, it is shown again.
     */
    fun switchChanged() {
        val choice = moduleChoice
        val oldNotification: Notification?
        val newNotification: Notification?
        synchronized(choiceLock) {
            val shown = choiceNotification?.takeUnless { it.isExpired }
            if (choice is ModuleChoice.Waiting && !project.isRobotCodeDisabled) {
                if (shown != null) {
                    return
                }
                oldNotification = null
                newNotification = moduleChoiceNotification(project, choice.candidates)
            } else {
                oldNotification = shown
                newNotification = null
            }
            choiceNotification = newNotification
        }
        oldNotification?.expire()
        newNotification?.notify(project)
    }

    // A new project interpreter is checked and restarts the server in a Robot Framework project. The restart waits for
    // the check; it also starts a server whose start failed with the last interpreter. It is requested first, so that
    // the result of the check does not start the server a second time. During a detection the last interpreter stays,
    // and the first interpreter, before the startup activity watches the workspace model, is no change.
    private fun followProjectInterpreter(): Boolean {
        val current = projectChoice()
        if (current.resolution.choice == ModuleChoice.Detecting) {
            return false
        }
        val interpreter = current.interpreter
        synchronized(choiceLock) {
            val last = lastInterpreter
            lastInterpreter = interpreter
            if (last == null || interpreter == last) {
                return false
            }
        }
        if (isRobotProject || project.langServerManager.isRunning) {
            project.restartAll()
        }
        if (isRobotProject) {
            checks.reset(interpreter)
        }
        return true
    }

    // tells the listeners about a changed choice that left the interpreter as it was, such as the request to choose
    private fun publishProjectState() {
        if (!project.isDisposed) {
            val (interpreter, state) = projectInterpreterAndState
            project.messageBus.syncPublisher(TOPIC).stateChanged(interpreter, state)
        }
    }

    /** Logs a changed choice and shows or removes the request to choose; returns whether the choice changed. */
    private fun noteModuleChoice(): Boolean {
        val current = projectChoice()
        val resolution = current.resolution
        val choice = resolution.choice
        val oldNotification: Notification?
        val newNotification: Notification?
        synchronized(choiceLock) {
            if (choice == lastChoice) {
                return false
            }
            lastChoice = choice
            oldNotification = choiceNotification
            newNotification = (choice as? ModuleChoice.Waiting)?.takeUnless { project.isRobotCodeDisabled }?.let {
                moduleChoiceNotification(project, it.candidates)
            }
            choiceNotification = newNotification
        }
        thisLogger().info(
            when (choice) {
                is ModuleChoice.Resolved -> "RobotCode uses the module ${choice.moduleName ?: "(none)"} with the " +
                    "Python interpreter ${current.interpreter.homePath ?: "(none)"}: ${resolution.reason}"

                is ModuleChoice.Waiting -> "RobotCode waits for the choice of one of the modules " +
                    "${choice.candidates.joinToString()}: ${resolution.reason}"

                ModuleChoice.Detecting -> "RobotCode waits for the module: ${resolution.reason}"
            }
        )
        oldNotification?.expire()
        newNotification?.notify(project)
        return true
    }

    // a choice that depends on the detection is detected again; the last result stays in use meanwhile
    private fun redetectModules() {
        val modules = pythonModules().map { it.name }
        if (modules.size > 1 && RobotCodePersonalConfiguration.getInstance(project).pythonModule !in modules) {
            detectModules(modules, again = true)
        }
    }

    // Starts the detection for [modules] unless one runs for them; with [again], a running one is repeated once it is
    // done, so that frequent changes do not keep it from finishing. A detection for other modules is replaced.
    private fun detectModules(modules: List<String>, again: Boolean) {
        synchronized(choiceLock) {
            if (detectionModules == modules && detectionJob?.isActive == true) {
                if (again) {
                    detectionAgain = true
                }
                return
            }
            detectionJob?.cancel()
            detectionModules = modules
            detectionAgain = false
            detectionsStarted.incrementAndGet()
            detectionJob = scope.launch {
                val job = coroutineContext[Job]
                do {
                    detectionFinished(ModuleDetection(modules, detectRobotFrameworkModules(modules)))
                    val repeat = synchronized(choiceLock) {
                        if (detectionJob !== job) {
                            false
                        } else if (detectionAgain) {
                            detectionAgain = false
                            true
                        } else {
                            // a later request starts a new detection
                            detectionModules = null
                            false
                        }
                    }
                } while (repeat)
            }
        }
    }

    private suspend fun detectRobotFrameworkModules(modules: List<String>): List<String> {
        return try {
            smartReadAction(project) {
                val manager = ModuleManager.getInstance(project)
                modules.filter { manager.findModuleByName(it)?.let(::isRobotFrameworkModule) == true }
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            // without a result the first module stays the rule, as before the detection existed
            thisLogger().warn("The detection of the Robot Framework projects among the modules failed", e)
            emptyList()
        }
    }

    private fun detectionFinished(result: ModuleDetection) {
        thisLogger().info(
            "The Robot Framework projects among the modules ${result.modules.joinToString()}: " +
                result.robotModules.joinToString().ifEmpty { "none" }
        )
        detection = result
        // logged with the reason of the detection, before the module is stored
        val choiceChanged = noteModuleChoice()
        // the only Robot Framework project is stored, so that the next opening does not wait for the index
        result.robotModules.singleOrNull()?.let { single ->
            val settings = RobotCodePersonalConfiguration.getInstance(project)
            if (settings.pythonModule !in result.modules) {
                settings.pythonModule = single
            }
        }
        if (choiceChanged && !followProjectInterpreter()) {
            publishProjectState()
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
