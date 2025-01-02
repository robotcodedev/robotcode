package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.LanguageServerEnablementSupport
import com.redhat.devtools.lsp4ij.LanguageServerFactory
import com.redhat.devtools.lsp4ij.client.LanguageClientImpl
import com.redhat.devtools.lsp4ij.server.StreamConnectionProvider
import dev.robotcode.robotcode4ij.lsp.RobotCodeLanguageServerManager.Companion.LANGUAGE_SERVER_ENABLED_KEY

class RobotCodeLanguageServerFactory : LanguageServerFactory, LanguageServerEnablementSupport {
    override fun createConnectionProvider(project: Project): StreamConnectionProvider {
        return RobotCodeLanguageServer(project)
    }
    
    override fun createLanguageClient(project: Project): LanguageClientImpl {
        return RobotCodeLanguageClient(project)
    }
    
    override fun isEnabled(project: Project): Boolean {
        if (project.getUserData(LANGUAGE_SERVER_ENABLED_KEY) == true) {
            return true
        }
        
        return project.langServerManager.tryConfigureProject()
    }
    
    override fun setEnabled(enabled: Boolean, project: Project) {
        project.putUserData(LANGUAGE_SERVER_ENABLED_KEY, enabled)
    }
}

