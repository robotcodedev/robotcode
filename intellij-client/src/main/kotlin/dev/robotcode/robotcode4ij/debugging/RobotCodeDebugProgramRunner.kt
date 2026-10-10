package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.configurations.RunProfile
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.RunnerSettings
import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.runners.AsyncProgramRunner
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.ui.RunContentDescriptor
import com.intellij.xdebugger.XDebugProcess
import com.intellij.xdebugger.XDebugProcessStarter
import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.XDebuggerManager
import dev.robotcode.robotcode4ij.execution.RobotCodeRunConfiguration
import dev.robotcode.robotcode4ij.execution.RobotCodeRunProfileState
import dev.robotcode.robotcode4ij.execution.startInBackground
import org.jetbrains.concurrency.Promise

class RobotCodeDebugProgramRunner : AsyncProgramRunner<RunnerSettings>() {
    override fun getRunnerId(): String {
        return "dev.robotcode.robotcode4ij.execution.RobotCodeDebugProgramRunner"
    }

    override fun canRun(executorId: String, profile: RunProfile): Boolean {
        return (executorId == DefaultDebugExecutor.EXECUTOR_ID) && profile is RobotCodeRunConfiguration
    }

    // the session wraps the started run; the debug process subscribes to the handshake before the session starts it
    override fun execute(environment: ExecutionEnvironment, state: RunProfileState): Promise<RunContentDescriptor?> {
        val runState = state as RobotCodeRunProfileState
        return startInBackground(runState, environment) { result ->
            XDebuggerManager.getInstance(environment.project).newSessionBuilder(object : XDebugProcessStarter() {
                override fun start(session: XDebugSession): XDebugProcess {
                    return RobotCodeDebugProcess(session, result, runState)
                }
            }).environment(environment).startSession().runContentDescriptor
        }
    }
}
