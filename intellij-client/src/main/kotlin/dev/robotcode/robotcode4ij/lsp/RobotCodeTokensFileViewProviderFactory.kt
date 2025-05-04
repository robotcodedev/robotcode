package dev.robotcode.robotcode4ij.lsp

import com.intellij.lang.Language
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.FileViewProvider
import com.intellij.psi.FileViewProviderFactory
import com.intellij.psi.PsiManager
import com.redhat.devtools.lsp4ij.features.semanticTokens.viewProvider.LSPSemanticTokensFileViewProvider
import com.redhat.devtools.lsp4ij.features.semanticTokens.viewProvider.LSPSemanticTokensSingleRootFileViewProvider
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage

class RobotCodeTokensFileViewProviderFactory : FileViewProviderFactory {
    override fun createFileViewProvider(
        file: VirtualFile,
        language: Language?,
        manager: PsiManager,
        eventSystemEnabled: Boolean
    ): FileViewProvider {
        if (language == RobotFrameworkLanguage) {
            return RobotCodeTokensFileViewProvider(manager, file, eventSystemEnabled, language)
        }
        throw UnsupportedOperationException("Unsupported language: $language or file: $file")
    }
}

class RobotCodeTokensFileViewProvider(
    manager: PsiManager,
    file: VirtualFile,
    eventSystemEnabled: Boolean,
    language: Language
) : LSPSemanticTokensSingleRootFileViewProvider(manager, file, eventSystemEnabled, language),
    LSPSemanticTokensFileViewProvider {
    
    
}
