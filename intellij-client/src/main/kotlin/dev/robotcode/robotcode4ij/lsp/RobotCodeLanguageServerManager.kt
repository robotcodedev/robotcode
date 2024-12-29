package dev.robotcode.robotcode4ij.lsp

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.util.ExecUtil
import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Key
import com.intellij.openapi.util.removeUserData
import com.jetbrains.python.sdk.pythonSdk
import com.redhat.devtools.lsp4ij.LanguageServerManager
import com.redhat.devtools.lsp4ij.ServerStatus
import dev.robotcode.robotcode4ij.BundledHelpers
import kotlin.io.path.Path
import kotlin.io.path.exists
import kotlin.io.path.isRegularFile
import kotlin.io.path.pathString

@Service(Service.Level.PROJECT)
class RobotCodeLanguageServerManager(private val project: Project) {
    companion object {
        const val LANGUAGE_SERVER_ID = "RobotCode"
        val ENABLED_KEY = Key.create<Boolean?>("ROBOTCODE_ENABLED")
    }
    
    fun tryConfigureProject(): Boolean {
        val pythonInterpreter = project.pythonSdk?.homePath
        
        project.removeUserData(ENABLED_KEY)
        
        val result = ApplicationManager.getApplication().executeOnPooledThread<Boolean> {
            checkPythonAndRobot(pythonInterpreter)
        }.get()
        
        project.putUserData(ENABLED_KEY, result)
        
        return result
    }
    
    private fun checkPythonAndRobot(pythonInterpreter: String?): Boolean {
        if (pythonInterpreter == null) {
            thisLogger().info("No Python Interpreter defined for project '${project.name}'")
            return false
        }
        
        if (!Path(pythonInterpreter).exists()) {
            thisLogger().warn("Python Interpreter $pythonInterpreter not exists")
            return false
        }
        
        if (!Path(pythonInterpreter).isRegularFile()) {
            thisLogger().warn("Python Interpreter $pythonInterpreter is not a regular file")
            return false
        }
        
        thisLogger().info("Use Python Interpreter $pythonInterpreter for project '${project.name}'")
        
        val res = ExecUtil.execAndGetOutput(
            GeneralCommandLine(
                pythonInterpreter, "-u", "-c",
                "import sys; print(sys.version_info[:2]>=(3,8))"
            ), timeoutInMilliseconds = 5000
        )
        if (res.exitCode != 0 || res.stdout.trim() != "True") {
            thisLogger().warn("Invalid python version")
            return false
        }
        
        val res1 = ExecUtil.execAndGetOutput(
            GeneralCommandLine(pythonInterpreter, "-u", BundledHelpers.checkRobotVersion.pathString),
            timeoutInMilliseconds = 5000
        )
        if (res1.exitCode != 0 || res1.stdout.trim() != "True") {
            thisLogger().warn("Invalid Robot Framework version")
            return false
        }
        
        return true
    }
    
    private var lease: Disposable? = null
    
    fun start() {
        if (lease != null) {
            lease!!.dispose()
            lease = null
        }
        
        if (tryConfigureProject()) {
            
            val options = LanguageServerManager.StartOptions()
            options.setForceStart(true)
            
            LanguageServerManager.getInstance(project).start(LANGUAGE_SERVER_ID, options)
            LanguageServerManager.getInstance(project).getLanguageServer(LANGUAGE_SERVER_ID).thenApply { server ->
                this.lease = server?.keepAlive()
            }
        }
    }
    
    fun stop() {
        if (lease != null) {
            lease!!.dispose()
            lease = null
        }
        LanguageServerManager.getInstance(project).stop(LANGUAGE_SERVER_ID)
    }
    
    fun restart() {
        stop()
        start()
    }
    
    val status: ServerStatus?
        get() {
            return LanguageServerManager.getInstance(project).getServerStatus(LANGUAGE_SERVER_ID)
        }
}

val Project.langServerManager: RobotCodeLanguageServerManager
    get() {
        return this.service<RobotCodeLanguageServerManager>()
    }
