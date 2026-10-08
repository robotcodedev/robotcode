package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.Disposable
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Key
import com.intellij.openapi.util.removeUserData
import com.intellij.platform.ide.progress.withBackgroundProgress
import com.redhat.devtools.lsp4ij.LanguageServerManager
import com.redhat.devtools.lsp4ij.ServerStatus
import dev.robotcode.robotcode4ij.CheckPythonAndRobotVersionResult
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.checkPythonAndRobotVersion
import dev.robotcode.robotcode4ij.restartAll
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.future.await
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.time.Duration.Companion.seconds

@Service(Service.Level.PROJECT)
class RobotCodeLanguageServerManager(private val project: Project, private val scope: CoroutineScope) {
    companion object {
        const val LANGUAGE_SERVER_ID = "RobotCode"
        val LANGUAGE_SERVER_ENABLED_KEY = Key.create<Boolean?>("ROBOTCODE_LANGUAGE_SERVER_ENABLED")
        private val CLEAR_CACHE_TIMEOUT = 30.seconds
    }
    
    fun tryConfigureProject(): Boolean {
        project.removeUserData(LANGUAGE_SERVER_ENABLED_KEY)
        
        val result = project.checkPythonAndRobotVersion() == CheckPythonAndRobotVersionResult.OK
        
        project.putUserData(LANGUAGE_SERVER_ENABLED_KEY, result)
        
        return result
    }
    
    private var lease: Disposable? = null
    
    /**
     * Set when a start of the server failed. LSP4IJ then does not start the server on its own, for example for an
     * editor that needs it, until a start through this manager clears it.
     */
    @Volatile
    var isStartBlocked = false
        private set
    
    fun reportStartFailure() {
        isStartBlocked = true
    }
    
    internal fun allowStart() {
        isStartBlocked = false
    }
    
    fun start() {
        if (lease != null) {
            lease!!.dispose()
            lease = null
        }
        
        allowStart()
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
        thisLogger().info("Restarting language server")
        stop()
        start()
    }
    
    /**
     * Clears the analysis cache of a running server, then restarts the server, which checks the environment again.
     */
    fun clearCacheAndRestart() {
        scope.launch {
            withBackgroundProgress(project, RobotCodeBundle.message("languageServer.clearCache.progress")) {
                // getLanguageServer() would start a stopped server and wait until it is initialized
                if (status == ServerStatus.started) {
                    clearCache()
                }
                project.restartAll(reset = true)
            }
        }
    }
    
    private suspend fun clearCache() {
        try {
            val cleared = withTimeoutOrNull(CLEAR_CACHE_TIMEOUT) {
                val server = LanguageServerManager.getInstance(project).getLanguageServer(LANGUAGE_SERVER_ID).await()
                (server?.server as? RobotCodeServerApi)?.clearCache()?.await()
                true
            }
            if (cleared == null) {
                thisLogger().warn("The language server did not clear its cache within $CLEAR_CACHE_TIMEOUT")
            }
        } catch (e: Exception) {
            // ends a cancelled coroutine; a failed or cancelled request is only logged
            currentCoroutineContext().ensureActive()
            thisLogger().warn("The language server could not clear its cache", e)
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
