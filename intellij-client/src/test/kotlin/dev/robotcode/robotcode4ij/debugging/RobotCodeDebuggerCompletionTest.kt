package dev.robotcode.robotcode4ij.debugging

import com.intellij.codeInsight.editorActions.TypedHandlerDelegate
import com.intellij.codeInsight.lookup.LookupElementPresentation
import com.intellij.icons.AllIcons
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import org.eclipse.lsp4j.debug.CompletionItem
import org.eclipse.lsp4j.debug.CompletionItemType

class RobotCodeDebuggerCompletionTest : BasePlatformTestCase() {

    private fun item(label: String, type: CompletionItemType, detail: String? = null) = CompletionItem().apply {
        this.label = label
        text = label
        this.type = type
        this.detail = detail
    }

    private fun presentationOf(item: CompletionItem): LookupElementPresentation {
        return LookupElementPresentation.renderElement(lookupElementOf(item))
    }

    fun testAKeywordShowsItsShortDocumentation() {
        val element = lookupElementOf(item("Log", CompletionItemType.FUNCTION, "Logs the given message."))
        val presentation = LookupElementPresentation.renderElement(element)

        assertEquals("Log", element.lookupString)
        assertEquals("Log", presentation.itemText)
        assertEquals(" Logs the given message.", presentation.tailText)
        assertSame(AllIcons.Nodes.Function, presentation.icon)
    }

    fun testAVariable() {
        val presentation = presentationOf(item("\${message}", CompletionItemType.VARIABLE))

        assertEquals("\${message}", presentation.itemText)
        assertNull(presentation.tailText)
        assertSame(AllIcons.Nodes.Variable, presentation.icon)
    }

    fun testALibraryOrResource() {
        assertSame(AllIcons.Nodes.Module, presentationOf(item("BuiltIn", CompletionItemType.MODULE)).icon)
        assertSame(AllIcons.Nodes.Module, presentationOf(item("common", CompletionItemType.MODULE)).icon)
    }

    private fun braceTypedInto(text: String, debuggerFile: Boolean): TypedHandlerDelegate.Result {
        myFixture.configureByText("dummy.robot", text)
        myFixture.file.putUserData(DEBUGGER_EXPRESSION_FILE, if (debuggerFile) true else null)
        return RobotCodeDebuggerTypedHandler().checkAutoPopup('{', project, myFixture.editor, myFixture.file)
    }

    fun testABraceAfterAVariableSignOpensTheListInTheDebuggersFiles() {
        assertEquals(TypedHandlerDelegate.Result.STOP, braceTypedInto("Log    \$<caret>", true))
        assertEquals(TypedHandlerDelegate.Result.STOP, braceTypedInto("Log    @<caret>", true))
        assertEquals(TypedHandlerDelegate.Result.CONTINUE, braceTypedInto("Log    x<caret>", true))
        assertEquals(TypedHandlerDelegate.Result.CONTINUE, braceTypedInto("Log    \$<caret>", false))
    }

    fun testTheCellBeforeTheCaretFiltersTheItems() {
        assertEquals("Lo", cellPrefix("Lo", 2))
        assertEquals("\${me", cellPrefix("Log    \${me", 11))
        assertEquals("Log To", cellPrefix("Log To", 6))
        assertEquals("", cellPrefix("Log    ", 7))
        assertEquals("x", cellPrefix("Log\tx", 5))
    }

    fun testAVariableStillOpenInTheCellFiltersTheItems() {
        fun prefix(text: String) = cellPrefix(text, text.length)

        assertEquals("\${me", prefix("Log    value is \${me"))
        assertEquals("\${", prefix("\${i} == 3 and \${"))
        assertEquals("@{it", prefix("Log Many    @{it"))
        assertEquals("\${", prefix("Log    \${name_\${"))
        assertEquals("\${GREETING} and", prefix("Log    \${GREETING} and"))
        assertEquals("\${{", prefix("Log    \${{"))
    }
}
