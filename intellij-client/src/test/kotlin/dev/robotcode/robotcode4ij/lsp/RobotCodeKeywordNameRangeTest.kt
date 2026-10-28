package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiFile
import com.intellij.testFramework.fixtures.BasePlatformTestCase

class RobotCodeKeywordNameRangeTest : BasePlatformTestCase() {

    private val suite = """
        *** Test Cases ***
        First
            Open Shop As    alice

        *** Keywords ***
        Open Shop As
            [Arguments]    ${'$'}{user}
            Log    ${'$'}{user}

        Open ${'$'}{url} In Browser
            No Operation
    """.trimIndent() + "\n"

    private lateinit var file: PsiFile

    private val tokens: RobotCodeTokensFileViewProvider
        get() = file.viewProvider as RobotCodeTokensFileViewProvider

    override fun setUp() {
        super.setUp()
        file = myFixture.configureByText("suite.robot", suite)
    }

    // the range of the [n]th occurrence of [word], counted from 0
    private fun rangeOf(word: String, n: Int = 0): TextRange {
        var start = -1
        repeat(n + 1) { start = suite.indexOf(word, start + 1) }
        assertTrue("no '$word' in the suite", start >= 0)
        return TextRange(start, start + word.length)
    }

    // as the server sends them: names of definitions with the modifier `declaration`
    private fun token(range: TextRange, type: String, vararg modifiers: String) =
        tokens.addSemanticToken(range, type, modifiers.toList())

    private fun addServerTokens() {
        token(rangeOf("First"), "testcaseName", "declaration")
        token(rangeOf("Open Shop As"), "keywordCall")
        token(rangeOf("Open Shop As", 1), "keywordName", "declaration")
        token(rangeOf("user"), "parameter")
        token(rangeOf("user", 1), "variable")
        token(rangeOf("Open ", 2), "keywordName", "declaration")
        token(rangeOf("url"), "variable")
        token(rangeOf(" In Browser"), "keywordName", "declaration")
    }

    fun testTheRecordKeepsTheServersType() {
        addServerTokens()

        assertEquals("keywordName", tokens.semanticTokenTypeAt(rangeOf("Open Shop As", 1).startOffset))
    }

    fun testTheNameOfAKeywordDefinition() {
        addServerTokens()
        val name = rangeOf("Open Shop As", 1)

        assertEquals(name, tokens.keywordNameRangeIn(name))
        assertEquals(name, tokens.keywordNameRangeIn(TextRange(name.startOffset + 3, name.endOffset)))
        assertEquals(name, tokens.keywordNameRangeIn(TextRange(name.startOffset - 1, name.endOffset + 1)))
    }

    fun testTheFirstPartOfANameWithAnEmbeddedArgument() {
        addServerTokens()
        val cell = TextRange(rangeOf("Open ", 2).startOffset, rangeOf(" In Browser").endOffset)

        assertEquals(rangeOf("Open ", 2), tokens.keywordNameRangeIn(cell))
    }

    fun testNoKeywordName() {
        addServerTokens()

        assertNull(tokens.keywordNameRangeIn(rangeOf("Open Shop As")))
        assertNull(tokens.keywordNameRangeIn(rangeOf("First")))
        assertNull(tokens.keywordNameRangeIn(rangeOf("user")))
        assertNull(tokens.keywordNameRangeIn(rangeOf("url")))
    }

    fun testAFileWithoutTokens() {
        assertNull(tokens.keywordNameRangeIn(rangeOf("Open Shop As", 1)))
    }
}
