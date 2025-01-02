package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.CommandLineState
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.KillableProcessHandler
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.process.ProcessTerminatedListener

import com.intellij.execution.runners.ExecutionEnvironment
import com.jetbrains.python.sdk.pythonSdk
import dev.robotcode.robotcode4ij.RobotCodeHelpers
import kotlin.io.path.pathString

class RobotCodeRunProfileState(environment: ExecutionEnvironment) : CommandLineState(environment) {
    override fun startProcess(): ProcessHandler {
        val project = environment.project
        val pythonInterpreter = project.pythonSdk?.homePath
            ?: throw IllegalArgumentException("PythonSDK is not defined for project ${project.name}")
        
        val commandLine = GeneralCommandLine(
            pythonInterpreter, "-u", "-X", "utf8",
            RobotCodeHelpers.robotCodePath.pathString,
            //"--log", "--log-level", "DEBUG",
            // "--debugpy",
            // "--debugpy-wait-for-client"
            "run"
        ).withWorkDirectory(project.basePath).withCharset(Charsets.UTF_8)
        val handler = KillableProcessHandler(commandLine)
        ProcessTerminatedListener.attach(handler)
        return handler
    }
    
}
