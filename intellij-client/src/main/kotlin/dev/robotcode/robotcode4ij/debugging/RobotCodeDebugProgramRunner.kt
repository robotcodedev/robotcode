package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.configurations.RunProfile
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.RunnerSettings
import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.runners.AsyncProgramRunner
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.ui.RunContentDescriptor
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.xdebugger.XDebugProcess
import com.intellij.xdebugger.XDebugProcessStarter
import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.XDebuggerManager
import dev.robotcode.robotcode4ij.execution.RobotCodeRunConfiguration
import dev.robotcode.robotcode4ij.execution.RobotCodeRunProfileState
import org.jetbrains.concurrency.Promise
import org.jetbrains.concurrency.resolvedPromise

class RobotCodeDebugProgramRunner : AsyncProgramRunner<RunnerSettings>() {
    override fun getRunnerId(): String {
        return "dev.robotcode.robotcode4ij.execution.RobotCodeDebugProgramRunner"
    }
    
    override fun canRun(executorId: String, profile: RunProfile): Boolean {
        return (executorId == DefaultDebugExecutor.EXECUTOR_ID) && profile is RobotCodeRunConfiguration
    }
    
    override fun execute(environment: ExecutionEnvironment, state: RunProfileState): Promise<RunContentDescriptor?> {
        FileDocumentManager.getInstance().saveAllDocuments()
        
        return resolvedPromise(doExecute(state as RobotCodeRunProfileState, environment))
    }
    
    private fun doExecute(state: RobotCodeRunProfileState, environment: ExecutionEnvironment): RunContentDescriptor {
        val manager = XDebuggerManager.getInstance(environment.project)
        val session = manager.startSession(environment, object : XDebugProcessStarter() {
            override fun start(session: XDebugSession): XDebugProcess {
                val result = state.execute(environment.executor, this@RobotCodeDebugProgramRunner)
                
                return RobotCodeDebugProcess(session, result, state)
            }
        })
        return session.runContentDescriptor
    }
}
