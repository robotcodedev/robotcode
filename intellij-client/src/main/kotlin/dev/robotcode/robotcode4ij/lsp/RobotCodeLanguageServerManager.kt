package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.Disposable
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Key
import com.intellij.openapi.util.removeUserData
import com.redhat.devtools.lsp4ij.LanguageServerManager
import com.redhat.devtools.lsp4ij.ServerStatus
import dev.robotcode.robotcode4ij.checkPythonAndRobotVersion
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking

@Service(Service.Level.PROJECT)
class RobotCodeLanguageServerManager(private val project: Project) {
    companion object {
        const val LANGUAGE_SERVER_ID = "RobotCode"
        val LANGUAGE_SERVER_ENABLED_KEY = Key.create<Boolean?>("ROBOTCODE_LANGUAGE_SERVER_ENABLED")
    }
    
    fun tryConfigureProject(): Boolean {
        project.removeUserData(LANGUAGE_SERVER_ENABLED_KEY)
        
        val result = project.checkPythonAndRobotVersion()
        
        project.putUserData(LANGUAGE_SERVER_ENABLED_KEY, result)
        
        return result
    }
    
    private var lease: Disposable? = null
    
    fun start() {
        if (lease != null) {
            lease!!.dispose()
            lease = null
        }
        
        if (tryConfigureProject()) {
            
            val options = LanguageServerManager.StartOptions()
            options.isForceStart = true
            
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
    
    fun clearCacheAndRestart() {
        runBlocking {
            val server = LanguageServerManager.getInstance(project).getLanguageServer(LANGUAGE_SERVER_ID).await()
            (server?.server as RobotCodeServerApi).clearCache()?.await()
            
            restart()
        }
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
