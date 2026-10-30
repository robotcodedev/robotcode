package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.ExecutionException
import com.intellij.execution.ExecutionListener
import com.intellij.execution.ExecutionManager
import com.intellij.execution.ExecutionResult
import com.intellij.execution.configurations.RunProfile
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.RunnerSettings
import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.runners.AsyncProgramRunner
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.runners.ExecutionEnvironmentBuilder
import com.intellij.execution.ui.RunContentDescriptor
import com.intellij.xdebugger.XDebugProcess
import com.intellij.xdebugger.XDebugProcessStarter
import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.XDebuggerManager
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.execution.isRobotRunProfile
import dev.robotcode.robotcode4ij.execution.RobotCodeRunConfiguration
import dev.robotcode.robotcode4ij.execution.RobotCodeRunProfileState
import dev.robotcode.robotcode4ij.execution.startInBackground
import org.jetbrains.concurrency.AsyncPromise
import org.jetbrains.concurrency.Promise

class RobotCodeDebugProgramRunner : AsyncProgramRunner<RunnerSettings>() {
    override fun getRunnerId(): String {
        return "dev.robotcode.robotcode4ij.execution.RobotCodeDebugProgramRunner"
    }

    override fun canRun(executorId: String, profile: RunProfile): Boolean {
        return (executorId == DefaultDebugExecutor.EXECUTOR_ID) && isRobotRunProfile(profile)
    }

    // the session wraps the started run; the debug process subscribes to the handshake before the session starts it
    override fun execute(environment: ExecutionEnvironment, state: RunProfileState): Promise<RunContentDescriptor?> {
        val runState = state as RobotCodeRunProfileState
        if (runState.currentRunDebugOptions().attachPython) {
            return startWithPythonSession(environment, runState)
        }
        return startInBackground(runState, environment) { result -> startRobotSession(environment, runState, result) }
    }

    private fun startRobotSession(
        environment: ExecutionEnvironment, state: RobotCodeRunProfileState, result: ExecutionResult
    ): RunContentDescriptor? {
        return XDebuggerManager.getInstance(environment.project).newSessionBuilder(object : XDebugProcessStarter() {
            override fun start(session: XDebugSession): XDebugProcess {
                return RobotCodeDebugProcess(session, result, state)
            }
        }).environment(environment).startSession().runContentDescriptor
    }

    // with "Attach Python", PyCharm's Python debug runner starts the run under pydevd in an environment of its own, the
    // Python tab; once the ExecutionManager has shown that tab, the Robot Framework session follows with the run's
    // handler and test tree console under the run's environment, whose tab this runner returns
    private fun startWithPythonSession(
        environment: ExecutionEnvironment, state: RobotCodeRunProfileState
    ): Promise<RunContentDescriptor?> {
        val promise = AsyncPromise<RunContentDescriptor?>()
        var runHandler: ProcessHandler? = null
        val pythonRunner = RobotCodePythonDebugRunner { runHandler = it }
        // without the run's settings: a rerun counts the run's session as the only one of the configuration, and each
        // session reuses the tab of its own name
        val pythonEnvironment = ExecutionEnvironmentBuilder(environment.project, environment.executor)
            .runProfile(pythonSessionConfiguration(state.config as RobotCodeRunConfiguration))
            .runner(pythonRunner)
            .target(environment.executionTarget)
            .build()
        pythonEnvironment.assignNewExecutionId()
        pythonEnvironment.putUserData(PYTHON_SESSION_RUN_STATE, state)
        pythonEnvironment.putUserData(PYTHON_SESSION_RUN_ENVIRONMENT, environment)
        val connection = environment.project.messageBus.connect()
        connection.subscribe(ExecutionManager.EXECUTION_TOPIC, object : ExecutionListener {
            override fun processStarted(executorId: String, env: ExecutionEnvironment, handler: ProcessHandler) {
                if (env !== pythonEnvironment) {
                    return
                }
                connection.disconnect()
                val run = runHandler
                val result = run?.let { state.robotSessionResult(it) }
                if (result == null) {
                    run?.let(::endRun)
                    promise.setError(notStarted())
                    return
                }
                try {
                    promise.setResult(startRobotSession(environment, state, result))
                } catch (e: Throwable) {
                    endRun(run)
                    promise.setError(e)
                }
            }

            override fun processNotStarted(executorId: String, env: ExecutionEnvironment, cause: Throwable?) {
                if (env !== pythonEnvironment) {
                    return
                }
                connection.disconnect()
                runHandler?.let(::endRun)
                promise.setError(cause ?: notStarted())
            }
        })
        state.pythonSession = true
        try {
            pythonRunner.execute(pythonEnvironment)
        } catch (e: Exception) {
            connection.disconnect()
            promise.setError(e)
        }
        return promise
    }

    private fun notStarted() = ExecutionException(RobotCodeBundle.message("debugger.pythonSession.notStarted"))
}

/**
 * Ends the run of a [handler] whose Robot Framework session did not start. Nothing has started the handler then, and a
 * handler that has not been started postpones its destruction until it is.
 */
internal fun endRun(handler: ProcessHandler) {
    if (!handler.isStartNotified) {
        handler.startNotify()
    }
    handler.destroyProcess()
}
