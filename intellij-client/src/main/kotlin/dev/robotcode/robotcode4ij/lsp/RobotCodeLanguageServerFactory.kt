package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.LanguageServerEnablementSupport
import com.redhat.devtools.lsp4ij.LanguageServerFactory
import com.redhat.devtools.lsp4ij.client.LanguageClientImpl
import com.redhat.devtools.lsp4ij.server.StreamConnectionProvider
import dev.robotcode.robotcode4ij.lsp.RobotCodeLanguageServerManager.Companion.ENABLED_KEY
import org.eclipse.lsp4j.services.LanguageServer

class RobotCodeLanguageServerFactory : LanguageServerFactory, LanguageServerEnablementSupport {
    override fun createConnectionProvider(project: Project): StreamConnectionProvider {
        return RobotCodeLanguageServer(project)
    }
    
    override fun createLanguageClient(project: Project): LanguageClientImpl {
        return RobotCodeLanguageClient(project)
    }
    
    override fun getServerInterface(): Class<out LanguageServer> {
        return super.getServerInterface()
    }
    
    override fun isEnabled(project: Project): Boolean {
        if (project.getUserData(ENABLED_KEY) == true) {
            return true
        }
        
        return project.langServerManager.tryConfigureProject()
    }
    
    override fun setEnabled(enabled: Boolean, project: Project) {
        project.putUserData(ENABLED_KEY, enabled)
    }
}

