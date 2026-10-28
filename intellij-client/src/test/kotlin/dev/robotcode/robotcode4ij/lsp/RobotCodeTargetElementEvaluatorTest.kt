package dev.robotcode.robotcode4ij.lsp

import com.intellij.codeInsight.TargetElementUtil
import com.intellij.codeInsight.TargetElementUtilBase
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.redhat.devtools.lsp4ij.usages.LSPUsageTriggeredPsiElement

class RobotCodeTargetElementEvaluatorTest : BasePlatformTestCase() {

    private val suite = """
        *** Test Cases ***
        First
            Open Shop As    alice

        *** Keywords ***
        Open Shop As
            [Arguments]    ${'$'}{user}
            Log    ${'$'}{user}
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

    // as the server sends them: names of definitions with the modifier `declaration`
    private fun token(range: TextRange, type: String, vararg modifiers: String) =
        (file.viewProvider as RobotCodeTokensFileViewProvider).addSemanticToken(range, type, modifiers.toList())

    private fun addServerTokens() {
        token(rangeOf("First"), "testcaseName", "declaration")
        token(rangeOf("Open Shop As"), "keywordCall")
        token(rangeOf("Open Shop As", 1), "keywordName", "declaration")
        token(rangeOf("user"), "parameter")
    }

    // what the IDE takes for a declaration in [range]: the named element of the lexer's leaf there
    private fun namedElementIn(range: TextRange): PsiElement? =
        TargetElementUtil.getNamedElement(file.findElementAt(range.startOffset + 1))

    fun testTheEvaluatorOfRobotFrameworkFiles() {
        assertInstanceOf(
            TargetElementUtilBase.getElementEvaluatorsEx2(file.language),
            RobotCodeTargetElementEvaluator::class.java
        )
    }

    fun testTheNameOfAKeywordDefinition() {
        addServerTokens()
        val name = rangeOf("Open Shop As", 1)

        val element = namedElementIn(name)

        assertInstanceOf(element, LSPUsageTriggeredPsiElement::class.java)
        assertEquals(file, element!!.containingFile)
        assertEquals(name, element.textRange)
    }

    fun testNoDeclaration() {
        addServerTokens()

        assertNull(namedElementIn(rangeOf("Open Shop As")))
        assertNull(namedElementIn(rangeOf("First")))
        assertNull(namedElementIn(rangeOf("user")))
    }

    fun testBeforeTheServerHasSentItsTokens() {
        assertNull(namedElementIn(rangeOf("Open Shop As", 1)))
    }
}
