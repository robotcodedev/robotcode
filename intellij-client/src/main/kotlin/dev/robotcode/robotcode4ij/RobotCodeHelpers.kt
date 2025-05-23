package dev.robotcode.robotcode4ij

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.util.ExecUtil
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.PathManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.modules
import com.intellij.openapi.util.Key
import com.jetbrains.python.sdk.pythonSdk
import dev.robotcode.robotcode4ij.lsp.langServerManager
import dev.robotcode.robotcode4ij.testing.testManger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
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
        
        val PYTHON_AND_ROBOT_OK_KEY = Key.create<CheckPythonAndRobotVersionResult?>("ROBOTCODE_PYTHON_AND_ROBOT_OK")
    }
}

val Project.robotPythonSdk: com.intellij.openapi.projectRoots.Sdk?
    get() {
        return this.pythonSdk ?: this.projectFile?.let {
            this.modules.firstNotNullOfOrNull { it.pythonSdk }
        }
    }

enum class CheckPythonAndRobotVersionResult(val errorMessage: String? = null) {
    OK(null),
    NO_PYTHON("No Python interpreter is configured for the project."),
    INVALID_PYTHON("The configured Python interpreter is invalid."),
    INVALID_PYTHON_VERSION("The Python version configured for the project is too old. Minimum required version is 3.9."),
    INVALID_ROBOT("The Robot Framework version is invalid or not installed. Version 5.0 or higher is required.")
}

fun Project.resetPythonAndRobotVersionCache() {
    this.putUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY, null)
}

fun Project.checkPythonAndRobotVersion(reset: Boolean = false): CheckPythonAndRobotVersionResult {
    if (!reset) {
        val cachedResult = this.getUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY)
        if (cachedResult != null) {
            return cachedResult
        }
    }
    
    val result = ApplicationManager.getApplication().executeOnPooledThread<CheckPythonAndRobotVersionResult> {
        
        val pythonInterpreter = this.robotPythonSdk?.homePath
        
        if (pythonInterpreter == null) {
            thisLogger().info("No Python Interpreter defined for project '${this.name}'")
            return@executeOnPooledThread CheckPythonAndRobotVersionResult.NO_PYTHON
        }
        
        if (!Path(pythonInterpreter).exists()) {
            thisLogger().warn("Python Interpreter $pythonInterpreter not exists")
            return@executeOnPooledThread CheckPythonAndRobotVersionResult.INVALID_PYTHON
        }
        
        if (!Path(pythonInterpreter).isRegularFile()) {
            thisLogger().warn("Python Interpreter $pythonInterpreter is not a regular file")
            return@executeOnPooledThread CheckPythonAndRobotVersionResult.INVALID_PYTHON
        }
        
        thisLogger().info("Use Python Interpreter $pythonInterpreter for project '${this.name}'")
        
        val res = ExecUtil.execAndGetOutput(
            GeneralCommandLine(
                pythonInterpreter, "-u", "-c", "import sys; print(sys.version_info[:2]>=(3,8))"
            ), timeoutInMilliseconds = 5000
        )
        if (res.exitCode != 0 || res.stdout.trim() != "True") {
            thisLogger().warn("Invalid python version")
            return@executeOnPooledThread CheckPythonAndRobotVersionResult.INVALID_PYTHON_VERSION
        }
        
        val res1 = ExecUtil.execAndGetOutput(
            GeneralCommandLine(pythonInterpreter, "-u", RobotCodeHelpers.checkRobotVersion.pathString),
            timeoutInMilliseconds = 5000
        )
        if (res1.exitCode != 0 || res1.stdout.trim() != "True") {
            thisLogger().warn("Invalid Robot Framework version")
            return@executeOnPooledThread CheckPythonAndRobotVersionResult.INVALID_ROBOT
        }
        
        return@executeOnPooledThread CheckPythonAndRobotVersionResult.OK
        
    }.get()
    
    this.putUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY, result)
    
    return result
}

class InvalidPythonOrRobotVersionException(message: String) : Exception(message)

fun Project.buildRobotCodeCommandLine(
    args: Array<String> = arrayOf(),
    profiles: Array<String> = arrayOf(),
    extraArgs: Array<String> = arrayOf(),
    format: String = "",
    noColor: Boolean = true,
    noPager: Boolean = true
): GeneralCommandLine {
    if (this.checkPythonAndRobotVersion() != CheckPythonAndRobotVersionResult.OK) {
        throw InvalidPythonOrRobotVersionException("PythonSDK is not defined or robot version is not valid for project ${this.name}")
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
        *profiles.flatMap { listOf("-p", it) }.toTypedArray(),
        *extraArgs,
        *args
    ).withWorkDirectory(this.basePath).withCharset(Charsets.UTF_8)
    
    return commandLine
}

@Service(Service.Level.PROJECT)
private class RobotCodeRestartManager(private val project: Project) {
    companion object {
        private const val DEBOUNCE_DELAY = 500L
    }
    
    private var refreshJob: Job? = null
    
    fun restart(reset: Boolean = false) {
        project.checkPythonAndRobotVersion(reset)
        project.langServerManager.restart()
        project.testManger.refreshDebounced()
    }
    
    @OptIn(ExperimentalCoroutinesApi::class)
    private val restartScope = CoroutineScope(Dispatchers.IO.limitedParallelism(1))
    
    fun restartDebounced(reset: Boolean = false) {
        if (!project.isOpen || project.isDisposed) {
            return
        }
        
        refreshJob?.cancel()
        
        refreshJob = restartScope.launch {
            delay(DEBOUNCE_DELAY)
            restart(reset)
            refreshJob = null
        }
    }
    
    fun cancelRestart() {
        refreshJob?.cancel()
        refreshJob = null
    }
}

fun Project.restartAll(reset: Boolean = false, debounced: Boolean = true) {
    val service = this.service<RobotCodeRestartManager>()
    if (debounced) {
        service.restartDebounced(reset)
    } else {
        service.cancelRestart()
        service.restart(reset)
    }
}
