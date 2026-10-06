package dev.robotcode.robotcode4ij.lsp

import com.intellij.lang.Language
import com.intellij.openapi.util.TextRange
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

    override fun addSemanticToken(textRange: TextRange, tokenType: String?, tokenModifiers: List<String>?) {
        if (hidesServerTokens(textRange, tokenModifiers, ::getSemanticTokenTextRange)) return
        super.addSemanticToken(textRange, tokenType, tokenModifiers)
    }
}

// After a successful Go to Declaration, LSP4IJ marks the whole PSI element as one reference token. It passes no
// modifiers, while tokens from the language server always come with a list. A keyword call such as
// `common.Start Case` is one PSI element, so that token would hide the server's tokens for `common` and
// `Start Case`, and every later jump would resolve at `common` and land on the import (issue #464).
internal fun hidesServerTokens(
    textRange: TextRange,
    tokenModifiers: List<String>?,
    tokenRangeAt: (Int) -> TextRange?
): Boolean {
    return tokenModifiers == null && (textRange.startOffset until textRange.endOffset).any { tokenRangeAt(it) != null }
}
