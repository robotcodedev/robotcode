package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.RunProfile
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.RunnerSettings
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.runners.AsyncProgramRunner
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.runners.showRunContent
import com.intellij.execution.ui.RunContentDescriptor
import com.intellij.openapi.fileEditor.FileDocumentManager
import org.jetbrains.concurrency.Promise
import org.jetbrains.concurrency.resolvedPromise

class RobotCodeProgramRunner : AsyncProgramRunner<RunnerSettings>() {
    override fun getRunnerId(): String {
        return "dev.robotcode.robotcode4ij.execution.RobotCodeProgramRunner"
    }
    
    override fun canRun(executorId: String, profile: RunProfile): Boolean {
        return (executorId == DefaultRunExecutor.EXECUTOR_ID) && profile is RobotCodeRunConfiguration
    }
    
    override fun execute(environment: ExecutionEnvironment, state: RunProfileState): Promise<RunContentDescriptor?> {
        FileDocumentManager.getInstance().saveAllDocuments()
        
        return resolvedPromise(doExecute(state as RobotCodeRunProfileState, environment))
    }
    
    private fun doExecute(state: RobotCodeRunProfileState, environment: ExecutionEnvironment): RunContentDescriptor? {
        return showRunContent(state.execute(environment.executor, this), environment)
    }
}
