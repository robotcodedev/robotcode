package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.CommandLineState
import com.intellij.execution.process.KillableProcessHandler
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.process.ProcessTerminatedListener
import com.intellij.execution.runners.ExecutionEnvironment
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine

class RobotCodeRunProfileState(environment: ExecutionEnvironment) : CommandLineState(environment) {
    override fun startProcess(): ProcessHandler {
        val project = environment.project
        val profile = environment.runProfile as? RobotCodeRunConfiguration
        // TODO: Add support for configurable paths
        val defaultPaths = arrayOf("--default-path", ".")
        
        val commandLine = project.buildRobotCodeCommandLine(arrayOf(*defaultPaths, "run"))
        
        val handler = KillableProcessHandler(commandLine)
        ProcessTerminatedListener.attach(handler)
        return handler
    }
    
}
