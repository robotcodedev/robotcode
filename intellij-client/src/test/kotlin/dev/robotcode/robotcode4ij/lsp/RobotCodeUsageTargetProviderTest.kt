package dev.robotcode.robotcode4ij.lsp

import com.intellij.find.findUsages.PsiElement2UsageTargetAdapter
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.usages.UsageTarget
import com.redhat.devtools.lsp4ij.features.LSPPsiElement
import com.redhat.devtools.lsp4ij.usages.LSPUsagePsiElement
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

    // the provider's targets for [element], with the caret of the open editor at [offset]
    private fun targetsFor(element: PsiElement, offset: Int = rangeOf("Log").startOffset + 1): Array<UsageTarget>? {
        myFixture.editor.caretModel.moveToOffset(offset)
        return RobotCodeUsageTargetProvider().getTargets(element)
    }

    // the element the name at the caret resolves to, which can lie in another file
    fun testResolvedDefinitionGetsTheNameAtTheCaret() {
        val definition = LSPPsiElement(myFixture.addFileToProject("library.txt", "def log"), TextRange(4, 7))

        val element = (targetsFor(definition)!!.single() as PsiElement2UsageTargetAdapter).element

        assertInstanceOf(element, LSPUsageTriggeredPsiElement::class.java)
        assertEquals(file, element.containingFile)
        assertEquals(rangeOf("Log"), element.textRange)
    }

    // the usages and the targets themselves, and elements of other views
    fun testOtherElementsGetNothing() {
        assertNull(targetsFor(LSPUsageTriggeredPsiElement(file, rangeOf("Log"))))
        assertNull(targetsFor(LSPUsagePsiElement(file, rangeOf("Log"))))
        assertNull(targetsFor(file))
    }

    fun testResolvedDefinitionWithoutATokenAtTheCaret() {
        assertNull(targetsFor(LSPPsiElement(file, rangeOf("Log")), rangeOf("First").startOffset))
    }

    fun testResolvedDefinitionInAnEditorOfAnotherFile() {
        val definition = LSPPsiElement(file, rangeOf("Log"))
        myFixture.configureByText("notes.txt", "Log")

        assertNull(RobotCodeUsageTargetProvider().getTargets(definition))
    }
}
