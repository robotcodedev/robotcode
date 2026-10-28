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
import java.util.concurrent.ConcurrentSkipListMap
import java.util.concurrent.atomic.AtomicReference

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

    // the types of the tokens, which LSP4IJ keeps to itself, for the current version of the file; held here and not in a
    // cached value, which the garbage collector may drop while LSP4IJ still has its tokens
    private val recorded = AtomicReference(RecordedTokens(-1))

    override fun addSemanticToken(textRange: TextRange, tokenType: String?, tokenModifiers: List<String>?) {
        if (hidesServerTokens(textRange, tokenModifiers, ::getSemanticTokenTextRange)) return
        super.addSemanticToken(textRange, standardTokenTypes[tokenType] ?: tokenType, tokenModifiers)
        if (tokenType == null || textRange.isEmpty) return
        val stamp = getPsi(baseLanguage)?.modificationStamp ?: return
        val tokens = recorded.updateAndGet { if (it.stamp == stamp) it else RecordedTokens(stamp) }
        tokens.byStart[textRange.startOffset] = RecordedToken(textRange.endOffset, tokenType)
    }

    // Only LSP4IJ's Go to Declaration handler asks these two. At a reference it resolves the target itself, and the IDE
    // then underlines the whole PSI element, such as `BuiltIn.Log` for `Log`. At a declaration it steps aside, and the
    // IDE takes the reference of the semantic token at the place, with the token's range.
    override fun isReference(offset: Int): Boolean = false

    override fun isDeclaration(offset: Int): Boolean = super.isDeclaration(offset) || super.isReference(offset)

    /** The type of the semantic token at [offset], as the language server sent it; null without a token. */
    internal fun semanticTokenTypeAt(offset: Int): String? = recordedTokenAt(offset)?.value?.type

    /** The range of the semantic token at [offset]; null without a token. */
    internal fun semanticTokenRangeAt(offset: Int): TextRange? =
        recordedTokenAt(offset)?.let { TextRange(it.key, it.value.endOffset) }

    /** The range of the first `keywordName` token that lies in [range], even in part; null without one. */
    internal fun keywordNameRangeIn(range: TextRange): TextRange? {
        val tokens = recorded.get()
        if (tokens.stamp != getPsi(baseLanguage)?.modificationStamp) return null
        // a token that starts before the range and reaches into it counts too
        val from = tokens.byStart.floorEntry(range.startOffset)?.takeIf { range.startOffset < it.value.endOffset }?.key
            ?: range.startOffset
        val token = tokens.byStart.subMap(from, range.endOffset).entries.firstOrNull { it.value.type == "keywordName" }
        return token?.let { TextRange(it.key, it.value.endOffset) }
    }

    private fun recordedTokenAt(offset: Int): Map.Entry<Int, RecordedToken>? {
        val tokens = recorded.get()
        if (tokens.stamp != getPsi(baseLanguage)?.modificationStamp) return null
        val token = tokens.byStart.floorEntry(offset) ?: return null
        return token.takeIf { offset < it.value.endOffset }
    }

    // by start offset: the server's tokens do not overlap
    private class RecordedTokens(val stamp: Long) {
        val byStart = ConcurrentSkipListMap<Int, RecordedToken>()
    }

    private class RecordedToken(val endOffset: Int, val type: String)
}

// LSP4IJ makes references and declarations only of tokens of the standard types. A reference is underlined on
// Ctrl+hover and resolved at its own place, so keyword calls get the standard type of a function call. The name in a
// keyword's definition gets it too: with the server's `declaration` modifier LSP4IJ takes it for a declaration, asks
// the server nothing on Ctrl+click there and shows the keyword's documentation on Ctrl+hover
private val standardTokenTypes =
    mapOf("keywordCall" to "function", "keywordCallInner" to "function", "keywordName" to "function")

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
