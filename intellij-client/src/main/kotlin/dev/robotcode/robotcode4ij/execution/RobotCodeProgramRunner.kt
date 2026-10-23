package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.ExecutionException
import com.intellij.execution.ExecutionResult
import com.intellij.execution.configurations.RunProfile
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.RunnerSettings
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.runners.AsyncProgramRunner
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.runners.showRunContent
import com.intellij.execution.ui.RunContentDescriptor
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.ModalityState
import com.intellij.openapi.fileEditor.FileDocumentManager
import dev.robotcode.robotcode4ij.RobotCodeBundle
import org.jetbrains.concurrency.AsyncPromise
import org.jetbrains.concurrency.Promise
import org.jetbrains.concurrency.rejectedPromise

/**
 * Starts the run of [state] on a background thread, because preparing the interpreter and its environment must not run
 * on the UI thread, and passes the result to [show] on the UI thread.
 */
internal fun startInBackground(
    state: RobotCodeRunProfileState,
    environment: ExecutionEnvironment,
    show: (ExecutionResult) -> RunContentDescriptor?
): Promise<RunContentDescriptor?> {
    FileDocumentManager.getInstance().saveAllDocuments()
    val promise = AsyncPromise<RunContentDescriptor?>()
    val application = ApplicationManager.getApplication()
    application.executeOnPooledThread {
        val result = try {
            state.execute(environment.executor)
        } catch (e: Throwable) {
            promise.setError(e)
            return@executeOnPooledThread
        }
        if (result == null) {
            promise.setResult(null)
            return@executeOnPooledThread
        }
        application.invokeLater({
            try {
                promise.setResult(show(result))
            } catch (e: Throwable) {
                result.processHandler?.destroyProcess()
                promise.setError(e)
            }
        }, ModalityState.nonModal())
    }
    return promise
}

class RobotCodeProgramRunner : AsyncProgramRunner<RunnerSettings>() {
    override fun getRunnerId(): String {
        return "dev.robotcode.robotcode4ij.execution.RobotCodeProgramRunner"
    }

    override fun canRun(executorId: String, profile: RunProfile): Boolean {
        return (executorId == DefaultRunExecutor.EXECUTOR_ID) && isRobotRunProfile(profile)
    }

    override fun execute(environment: ExecutionEnvironment, state: RunProfileState): Promise<RunContentDescriptor?> {
        return startInBackground(state as RobotCodeRunProfileState, environment) { showRunContent(it, environment) }
    }
}

// the ids of the executors of PyCharm Professional's "Profile" and "Concurrency Diagram"
private const val PROFILER_EXECUTOR_ID = "Profiler"
private const val CONCURRENCY_DIAGRAM_EXECUTOR_ID = "ConcurrencyExecutor"

/** The end of a run of [environment] with the message that Robot Framework runs do not support its executor. */
internal fun unsupportedRun(environment: ExecutionEnvironment): Promise<RunContentDescriptor?> {
    val key = when (environment.executor.id) {
        CONCURRENCY_DIAGRAM_EXECUTOR_ID -> "run.concurrencyDiagram.notSupported"
        else -> "run.profile.notSupported"
    }
    return rejectedPromise(ExecutionException(RobotCodeBundle.message(key)))
}

/**
 * Takes PyCharm Professional's "Profile" and "Concurrency Diagram" for Robot Framework configurations, which its
 * runners would otherwise accept as Python run configurations, and ends them with a message.
 */
class RobotCodeProfileRunner : AsyncProgramRunner<RunnerSettings>() {
    override fun getRunnerId(): String {
        return "dev.robotcode.robotcode4ij.execution.RobotCodeProfileRunner"
    }

    override fun canRun(executorId: String, profile: RunProfile): Boolean {
        return (executorId == PROFILER_EXECUTOR_ID || executorId == CONCURRENCY_DIAGRAM_EXECUTOR_ID) &&
            isRobotRunProfile(profile)
    }

    override fun execute(environment: ExecutionEnvironment, state: RunProfileState): Promise<RunContentDescriptor?> {
        return unsupportedRun(environment)
    }
}
