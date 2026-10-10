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
        return (executorId == DefaultRunExecutor.EXECUTOR_ID) && profile is RobotCodeRunConfiguration
    }

    override fun execute(environment: ExecutionEnvironment, state: RunProfileState): Promise<RunContentDescriptor?> {
        return startInBackground(state as RobotCodeRunProfileState, environment) { showRunContent(it, environment) }
    }
}

/**
 * Takes PyCharm Professional's "Profile" for Robot Framework configurations, which its profiler runner would otherwise
 * accept as Python run configurations, and ends it with a message.
 */
class RobotCodeProfileRunner : AsyncProgramRunner<RunnerSettings>() {
    override fun getRunnerId(): String {
        return "dev.robotcode.robotcode4ij.execution.RobotCodeProfileRunner"
    }
    
    // the id of PyCharm Professional's profiler executor
    override fun canRun(executorId: String, profile: RunProfile): Boolean {
        return executorId == "Profiler" && profile is RobotCodeRunConfiguration
    }
    
    override fun execute(environment: ExecutionEnvironment, state: RunProfileState): Promise<RunContentDescriptor?> {
        return rejectedPromise(ExecutionException(RobotCodeBundle.message("run.profile.notSupported")))
    }
}
