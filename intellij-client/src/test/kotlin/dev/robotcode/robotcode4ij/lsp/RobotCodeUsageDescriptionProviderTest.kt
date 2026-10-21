package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiFile
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.usageView.UsageViewTypeLocation
import com.intellij.usageView.UsageViewUtil
import com.redhat.devtools.lsp4ij.features.LSPPsiElement
import com.redhat.devtools.lsp4ij.usages.LSPUsageTriggeredPsiElement

class RobotCodeUsageDescriptionProviderTest : BasePlatformTestCase() {

    private val suite = """
        *** Settings ***
        Library    Collections

        *** Test Cases ***
        First
            [Tags]    smoke
            Given Open Shop As    alice
            Run Keyword And Expect Error    Wrong password    Open Shop As    alice
            Collections.Append To List    ${'$'}{items}    b
            Log    ${'$'}{GREETING}

        *** Keywords ***
        Open Shop As
            [Arguments]    ${'$'}{user}
            Log In    ${'$'}{user}
    """.trimIndent() + "\n"

    private lateinit var file: PsiFile

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

    private fun token(range: TextRange, type: String) =
        (file.viewProvider as RobotCodeTokensFileViewProvider).addSemanticToken(range, type, emptyList())

    // what Show Usages starts on: the place where it was started
    private fun usageTarget(range: TextRange) = LSPUsageTriggeredPsiElement(file, range)

    fun testKeywords() {
        val call = rangeOf("Open Shop As")
        val inner = rangeOf("Open Shop As", 1)
        val definition = rangeOf("Open Shop As", 2)
        val given = rangeOf("Given")
        token(call, "keywordCall")
        token(inner, "keywordCallInner")
        token(definition, "keywordName")
        token(given, "bddPrefix")

        for (range in listOf(call, inner, definition)) {
            assertEquals("keyword", UsageViewUtil.getType(usageTarget(range)))
            assertEquals("Open Shop As", UsageViewUtil.getLongName(usageTarget(range)))
        }
        assertEquals("keyword", UsageViewUtil.getType(usageTarget(given)))
    }

    // Show Usages on a keyword's argument works on the declaration that LSP4IJ resolved
    fun testArgument() {
        val declaration = rangeOf("user")
        token(declaration, "parameter")

        val element = LSPPsiElement(file, declaration)

        assertEquals("argument", UsageViewUtil.getType(element))
        assertEquals("user", UsageViewUtil.getLongName(element))
    }

    fun testVariable() {
        val variable = rangeOf("GREETING")
        token(variable, "variable")

        assertEquals("variable", UsageViewUtil.getType(usageTarget(variable)))
        assertEquals("GREETING", UsageViewUtil.getLongName(usageTarget(variable)))
        assertEquals("variable", UsageViewUtil.getType(LSPPsiElement(file, variable)))
        assertEquals("GREETING", UsageViewUtil.getLongName(LSPPsiElement(file, variable)))
    }

    fun testNamespaces() {
        val import = rangeOf("Collections")
        val prefix = rangeOf("Collections", 1)
        token(import, "namespace")
        token(prefix, "namespace")

        assertEquals("namespace", UsageViewUtil.getType(usageTarget(import)))
        assertEquals("Collections", UsageViewUtil.getLongName(usageTarget(import)))
        assertEquals("namespace", UsageViewUtil.getType(usageTarget(prefix)))
    }

    // before the language server has sent its tokens, the lexer tells keywords and variables apart
    fun testWithoutTokens() {
        assertEquals("keyword", UsageViewUtil.getType(usageTarget(rangeOf("Log In"))))
        assertEquals("variable", UsageViewUtil.getType(usageTarget(rangeOf("GREETING"))))
    }

    // the language server sends no token for a tag
    fun testTag() {
        assertEquals("symbol", UsageViewUtil.getType(usageTarget(rangeOf("smoke"))))
        assertEquals("smoke", UsageViewUtil.getLongName(usageTarget(rangeOf("smoke"))))
    }

    fun testOnlyRobotFrameworkFiles() {
        val notes = myFixture.configureByText("notes.txt", "Open Shop As")

        val element = LSPUsageTriggeredPsiElement(notes, TextRange(0, 12))

        assertNull(RobotCodeUsageDescriptionProvider().getElementDescription(element, UsageViewTypeLocation.INSTANCE))
    }
}
