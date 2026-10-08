package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.LanguageServerManager
import dev.robotcode.robotcode4ij.editor.updateRobotCodeStatusBar
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.future.await
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.time.Duration.Companion.seconds

/**
 * Keeps the versions that the running language server reports, for the status bar. Nothing waits for them.
 */
@Service(Service.Level.PROJECT)
class RobotCodeProjectInfoService(private val project: Project, private val scope: CoroutineScope) {
    companion object {
        private val TIMEOUT = 30.seconds
    }

    @Volatile
    var info: ProjectInfo? = null
        private set

    @Volatile
    private var job: Job? = null

    fun serverStarted() {
        job?.cancel()
        job = scope.launch {
            val received = try {
                withTimeoutOrNull(TIMEOUT) {
                    val server = LanguageServerManager.getInstance(project)
                        .getLanguageServer(RobotCodeLanguageServerManager.LANGUAGE_SERVER_ID).await()
                    (server?.server as? RobotCodeServerApi)?.projectInfo()?.await()
                }
            } catch (e: Exception) {
                // ends a cancelled coroutine; a failed request is only logged
                currentCoroutineContext().ensureActive()
                thisLogger().warn("The language server did not report the project information", e)
                null
            }
            info = received
            project.updateRobotCodeStatusBar()
        }
    }

    fun serverStopped() {
        job?.cancel()
        info = null
        project.updateRobotCodeStatusBar()
    }
}

val Project.robotCodeProjectInfo: RobotCodeProjectInfoService
    get() = this.service<RobotCodeProjectInfoService>()
