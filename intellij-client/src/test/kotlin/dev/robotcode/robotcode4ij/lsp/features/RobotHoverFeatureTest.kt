package dev.robotcode.robotcode4ij.lsp.features

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.util.ui.UIUtil
import org.eclipse.lsp4j.MarkupContent
import org.eclipse.lsp4j.MarkupKind

class RobotHoverFeatureTest : BasePlatformTestCase() {

    private fun contentOf(kind: String, value: String): String? {
        val file = myFixture.configureByText("suite.robot", "*** Test Cases ***\nFirst\n    Log    x\n")
        return RobotHoverFeature().getContent(MarkupContent(kind, value), file)
    }

    // the Ctrl+hover hint takes HTML without the element for text and turns its line breaks into `<br>`
    fun testMarkdownIsPutIntoAnHtmlElement() {
        val markdown = "### Keyword *Open Shop As*\n\n#### Arguments:\n\n| | |\n|:--|:--|\n| `user` | |\n\n" +
            "First paragraph.\n\nSecond paragraph.\n"

        val html = contentOf(MarkupKind.MARKDOWN, markdown)!!

        assertTrue(html.startsWith("<html>"))
        assertTrue(html.endsWith("</html>"))
        assertFalse(UIUtil.getHtmlBody(html).contains("<br>"))
    }

    fun testPlainTextStaysAsItIs() {
        assertEquals("first line\nsecond line", contentOf(MarkupKind.PLAINTEXT, "first line\nsecond line"))
    }
}
