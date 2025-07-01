package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.ServerStatus
import com.redhat.devtools.lsp4ij.client.IndexAwareLanguageClient
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration

class RobotCodeLanguageClient(project: Project) : IndexAwareLanguageClient(project) {
    
    override fun handleServerStatusChanged(serverStatus: ServerStatus) {
        if (serverStatus == ServerStatus.started) {
            triggerChangeConfiguration()
        }
    }
    
    override fun createSettings(): Any {
        return RobotCodeProjectConfiguration.getInstance(project).asJson()
    }
}
