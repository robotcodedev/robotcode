package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.ServerStatus
import com.redhat.devtools.lsp4ij.client.IndexAwareLanguageClient
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettingsMapper

class RobotCodeLanguageClient(project: Project) : IndexAwareLanguageClient(project) {
    
    override fun handleServerStatusChanged(serverStatus: ServerStatus) {
        when (serverStatus) {
            ServerStatus.started -> {
                triggerChangeConfiguration()
                project.robotCodeProjectInfo.serverStarted()
            }

            ServerStatus.stopping, ServerStatus.stopped -> project.robotCodeProjectInfo.serverStopped()
            else -> {}
        }
    }
    
    override fun createSettings(): Any {
        return RobotCodeServerSettingsMapper.toJsonTree(project)
    }
}
