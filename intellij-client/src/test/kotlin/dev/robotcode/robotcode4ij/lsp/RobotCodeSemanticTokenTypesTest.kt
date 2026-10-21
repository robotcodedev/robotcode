package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiFile
import com.intellij.testFramework.fixtures.BasePlatformTestCase

class RobotCodeSemanticTokenTypesTest : BasePlatformTestCase() {

    private fun suite(text: String): PsiFile = myFixture.configureByText("suite.robot", text)

    private fun PsiFile.rangeOf(word: String): TextRange = text.indexOf(word).let { TextRange(it, it + word.length) }

    private val PsiFile.tokens: RobotCodeTokensFileViewProvider
        get() = viewProvider as RobotCodeTokensFileViewProvider

    // LSP4IJ keeps no tokens without a running server, but the plugin records their types all the same
    private fun PsiFile.addToken(range: TextRange, type: String) = tokens.addSemanticToken(range, type, emptyList())

    fun testTheTypeOfATokenIsFoundOverItsRange() {
        val file = suite("*** Test Cases ***\nFirst\n    Open Shop As    alice\n")
        val call = file.rangeOf("Open Shop As")

        file.addToken(call, "keywordCall")

        for (offset in call.startOffset until call.endOffset) {
            assertEquals("keywordCall", file.tokens.semanticTokenTypeAt(offset))
        }
        assertNull(file.tokens.semanticTokenTypeAt(call.startOffset - 1))
        assertNull(file.tokens.semanticTokenTypeAt(call.endOffset))
    }

    // the dot of `Collections.Append To List` lies between two tokens
    fun testNeighbouringTokens() {
        val file = suite("*** Test Cases ***\nFirst\n    Collections.Append To List    ${'$'}{items}    b\n")
        val prefix = file.rangeOf("Collections")
        val call = file.rangeOf("Append To List")

        file.addToken(prefix, "namespace")
        file.addToken(call, "keywordCall")

        assertEquals("namespace", file.tokens.semanticTokenTypeAt(prefix.endOffset - 1))
        assertNull(file.tokens.semanticTokenTypeAt(prefix.endOffset))
        assertEquals("keywordCall", file.tokens.semanticTokenTypeAt(call.startOffset))
        assertEquals("keywordCall", file.tokens.semanticTokenTypeAt(call.endOffset - 1))
    }

    fun testAnEditDropsTheRecordedTypes() {
        val file = suite("*** Test Cases ***\nFirst\n    Open Shop As    alice\n")
        val call = file.rangeOf("Open Shop As")
        file.addToken(call, "keywordCall")

        WriteCommandAction.runWriteCommandAction(project) { myFixture.editor.document.insertString(0, "\n") }
        PsiDocumentManager.getInstance(project).commitAllDocuments()

        assertNull(file.tokens.semanticTokenTypeAt(call.startOffset))
        assertNull(file.tokens.semanticTokenTypeAt(call.startOffset + 1))
    }

    // the tokens of the new version replace those of the old one
    fun testTokensAfterAnEdit() {
        val file = suite("*** Test Cases ***\nFirst\n    Open Shop As    alice\n")
        file.addToken(file.rangeOf("Open Shop As"), "keywordCall")

        WriteCommandAction.runWriteCommandAction(project) { myFixture.editor.document.insertString(0, "\n") }
        PsiDocumentManager.getInstance(project).commitAllDocuments()
        file.addToken(file.rangeOf("alice"), "argument")

        assertEquals("argument", file.tokens.semanticTokenTypeAt(file.rangeOf("alice").startOffset))
        assertNull(file.tokens.semanticTokenTypeAt(file.rangeOf("Open Shop As").startOffset))
    }
}
