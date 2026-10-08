package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.LanguageServerEnablementSupport
import com.redhat.devtools.lsp4ij.LanguageServerFactory
import com.redhat.devtools.lsp4ij.client.LanguageClientImpl
import com.redhat.devtools.lsp4ij.client.features.LSPClientFeatures
import com.redhat.devtools.lsp4ij.server.StreamConnectionProvider
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.isRobotCodeDisabled
import dev.robotcode.robotcode4ij.languageServerEnabled
import dev.robotcode.robotcode4ij.lsp.features.RobotDiagnosticsFeature
import dev.robotcode.robotcode4ij.lsp.features.RobotSemanticTokensFeature
import dev.robotcode.robotcode4ij.robotCodeEnvironment
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
        val manager = project.langServerManager
        if (manager.isStartBlocked || manager.isDisabledForSession || project.isRobotCodeDisabled) {
            return false
        }
        
        // never waits for the check: without a result, LSP4IJ starts nothing yet, and a usable result starts the server
        val environment = project.robotCodeEnvironment
        val interpreter = environment.projectInterpreter
        val state = environment.state(interpreter)
        if (state == EnvironmentState.Unknown) {
            environment.requestCheck(interpreter)
        }
        return state.isUsable
    }
    
    // LSP4IJ disables the server from the Language Servers tool window and after repeated failed starts
    override fun setEnabled(enabled: Boolean, project: Project) {
        if (enabled) {
            project.languageServerEnabled()
        } else {
            project.langServerManager.disableForSession()
        }
    }
}

