package dev.robotcode.robotcode4ij

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.util.ExecUtil
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.PathManager
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.modules
import com.intellij.openapi.util.Key
import com.jetbrains.python.sdk.pythonSdk
import java.nio.file.Path
import kotlin.io.path.Path
import kotlin.io.path.exists
import kotlin.io.path.isRegularFile
import kotlin.io.path.pathString

class RobotCodeHelpers {
    companion object {
        val basePath: Path = PathManager.getPluginsDir().resolve("robotcode4ij").resolve("data")
        val bundledPath: Path = basePath.resolve("bundled")
        val toolPath: Path = bundledPath.resolve("tool")
        val robotCodePath: Path = toolPath.resolve("robotcode")
        val checkRobotVersion: Path = toolPath.resolve("utils").resolve("check_robot_version.py")
        
        val PYTHON_AND_ROBOT_OK_KEY = Key.create<Boolean?>("ROBOTCODE_PYTHON_AND_ROBOT_OK")
    }
}

val Project.robotPythonSdk: com.intellij.openapi.projectRoots.Sdk?
    get() {
        return this.pythonSdk ?: this.projectFile?.let {
            this.modules.firstNotNullOfOrNull { it.pythonSdk }
        }
    }

fun Project.checkPythonAndRobotVersion(reset: Boolean = false): Boolean {
    if (!reset && this.getUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY) == true) {
        return true
    }
    
    val result = ApplicationManager.getApplication().executeOnPooledThread<Boolean> {
        
        val pythonInterpreter = this.robotPythonSdk?.homePath
        
        if (pythonInterpreter == null) {
            thisLogger().info("No Python Interpreter defined for project '${this.name}'")
            return@executeOnPooledThread false
        }
        
        if (!Path(pythonInterpreter).exists()) {
            thisLogger().warn("Python Interpreter $pythonInterpreter not exists")
            return@executeOnPooledThread false
        }
        
        if (!Path(pythonInterpreter).isRegularFile()) {
            thisLogger().warn("Python Interpreter $pythonInterpreter is not a regular file")
            return@executeOnPooledThread false
        }
        
        thisLogger().info("Use Python Interpreter $pythonInterpreter for project '${this.name}'")
        
        val res = ExecUtil.execAndGetOutput(
            GeneralCommandLine(
                pythonInterpreter, "-u", "-c", "import sys; print(sys.version_info[:2]>=(3,8))"
            ), timeoutInMilliseconds = 5000
        )
        if (res.exitCode != 0 || res.stdout.trim() != "True") {
            thisLogger().warn("Invalid python version")
            return@executeOnPooledThread false
        }
        
        val res1 = ExecUtil.execAndGetOutput(
            GeneralCommandLine(pythonInterpreter, "-u", RobotCodeHelpers.checkRobotVersion.pathString),
            timeoutInMilliseconds = 5000
        )
        if (res1.exitCode != 0 || res1.stdout.trim() != "True") {
            thisLogger().warn("Invalid Robot Framework version")
            return@executeOnPooledThread false
        }
        
        return@executeOnPooledThread true
        
    }.get()
    
    this.putUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY, result)
    
    return result
}


fun Project.buildRobotCodeCommandLine(
    args: Array<String> = arrayOf(),
    profiles: Array<String> = arrayOf(),
    extraArgs: Array<String> = arrayOf(),
    format: String = "",
    noColor: Boolean = true,
    noPager: Boolean = true
): GeneralCommandLine {
    if (!this.checkPythonAndRobotVersion()) {
        throw IllegalArgumentException("PythonSDK is not defined or robot version is not valid for project ${this.name}")
    }
    
    val pythonInterpreter = this.robotPythonSdk?.homePath
    val commandLine = GeneralCommandLine(
        pythonInterpreter,
        "-u",
        "-X",
        "utf8",
        RobotCodeHelpers.robotCodePath.pathString,
        *(if (format.isNotEmpty()) arrayOf("--format", format) else arrayOf()),
        *(if (noColor) arrayOf("--no-color") else arrayOf()),
        *(if (noPager) arrayOf("--no-pager") else arrayOf()),
        *profiles.flatMap { listOf("--profile", it) }.toTypedArray(),
        *extraArgs,
        *args
    ).withWorkDirectory(this.basePath).withCharset(Charsets.UTF_8)
    
    return commandLine
}
