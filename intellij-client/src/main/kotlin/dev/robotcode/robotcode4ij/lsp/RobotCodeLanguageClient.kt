package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.ServerStatus
import com.redhat.devtools.lsp4ij.client.IndexAwareLanguageClient
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettingsMapper
import dev.robotcode.robotcode4ij.configuration.profileListCache

class RobotCodeLanguageClient(project: Project) : IndexAwareLanguageClient(project) {
    
    override fun handleServerStatusChanged(serverStatus: ServerStatus) {
        when (serverStatus) {
            ServerStatus.started -> {
                triggerChangeConfiguration()
                project.robotCodeProjectInfo.serverStarted()
                // the server also starts again after a change to robot.toml, which may change the profiles; the run
                // configurations' warning about profiles that no longer exist needs the list without a dialog open
                project.profileListCache.reload()
            }

            ServerStatus.stopping, ServerStatus.stopped -> project.robotCodeProjectInfo.serverStopped()
            else -> {}
        }
    }
    
    override fun createSettings(): Any {
        return RobotCodeServerSettingsMapper.toJsonTree(project)
    }
}
