package dev.robotcode.robotcode4ij.lsp

import com.intellij.find.findUsages.PsiElement2UsageTargetAdapter
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiFile
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.redhat.devtools.lsp4ij.usages.LSPUsageTriggeredPsiElement

class RobotCodeUsageTargetProviderTest : BasePlatformTestCase() {

    private val suite = "*** Test Cases ***\nFirst\n    BuiltIn.Log    x\n"

    private lateinit var file: PsiFile

    override fun setUp() {
        super.setUp()
        file = myFixture.configureByText("suite.robot", suite)
        token(rangeOf("BuiltIn"), "namespace")
        token(rangeOf("Log"), "keywordCall")
    }

    private fun rangeOf(word: String): TextRange = suite.indexOf(word).let { TextRange(it, it + word.length) }

    private fun token(range: TextRange, type: String) =
        (file.viewProvider as RobotCodeTokensFileViewProvider).addSemanticToken(range, type, emptyList())

    // the range of the provider's target with the caret at [offset]; null without a target
    private fun targetAt(offset: Int): TextRange? {
        myFixture.editor.caretModel.moveToOffset(offset)
        val targets = RobotCodeUsageTargetProvider().getTargets(myFixture.editor, file) ?: return null
        val element = (targets.single() as PsiElement2UsageTargetAdapter).element
        assertInstanceOf(element, LSPUsageTriggeredPsiElement::class.java)
        return element.textRange
    }

    // the caret right after the name, before the spaces, still belongs to it
    fun testKeywordAfterAPrefix() {
        val call = rangeOf("Log")

        for (offset in call.startOffset..call.endOffset) {
            assertEquals(call, targetAt(offset))
        }
    }

    // the dot after the prefix belongs to no token
    fun testPrefix() {
        val prefix = rangeOf("BuiltIn")

        for (offset in prefix.startOffset..prefix.endOffset) {
            assertEquals(prefix, targetAt(offset))
        }
    }

    fun testNoTokenAtTheCaret() {
        assertNull(targetAt(rangeOf("First").startOffset))
        assertNull(targetAt(rangeOf("x").startOffset))
        assertNull(targetAt(rangeOf("x").endOffset))
    }
}
