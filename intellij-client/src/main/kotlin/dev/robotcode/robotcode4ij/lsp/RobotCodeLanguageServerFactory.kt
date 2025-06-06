package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.LanguageServerEnablementSupport
import com.redhat.devtools.lsp4ij.LanguageServerFactory
import com.redhat.devtools.lsp4ij.client.LanguageClientImpl
import com.redhat.devtools.lsp4ij.client.features.LSPClientFeatures
import com.redhat.devtools.lsp4ij.server.StreamConnectionProvider
import dev.robotcode.robotcode4ij.lsp.RobotCodeLanguageServerManager.Companion.LANGUAGE_SERVER_ENABLED_KEY
import dev.robotcode.robotcode4ij.lsp.features.RobotDiagnosticsFeature
import dev.robotcode.robotcode4ij.lsp.features.RobotSemanticTokensFeature
import org.eclipse.lsp4j.services.LanguageServer

@Suppress("UnstableApiUsage") class RobotCodeLanguageServerFactory : LanguageServerFactory,
                                                                     LanguageServerEnablementSupport {
    override fun createConnectionProvider(project: Project): StreamConnectionProvider {
        return RobotCodeLanguageServer(project)
    }
    
    override fun createClientFeatures(): LSPClientFeatures {
        return super.createClientFeatures()
            .setDiagnosticFeature(RobotDiagnosticsFeature())
            .setSemanticTokensFeature(RobotSemanticTokensFeature())
    }
    
    override fun createLanguageClient(project: Project): LanguageClientImpl {
        return RobotCodeLanguageClient(project)
    }
    
    override fun getServerInterface(): Class<out LanguageServer?> {
        return RobotCodeServerApi::class.java
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

