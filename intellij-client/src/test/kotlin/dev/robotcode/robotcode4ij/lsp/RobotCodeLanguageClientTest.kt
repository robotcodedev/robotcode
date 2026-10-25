package dev.robotcode.robotcode4ij.lsp

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.redhat.devtools.lsp4ij.features.documentation.MarkdownConverter

class RobotCodeLanguageClientTest : BasePlatformTestCase() {

    // LSP4IJ turns the message of window/showMessage from Markdown into the HTML of its notification
    fun testAMessageOfTheServerKeepsEveryCharacter() {
        val message = "No profile matches '*base*'. invalid syntax (<unknown>, line 1)"

        val html = MarkdownConverter.getInstance(project).toHtml(escapeMarkdown(message))

        assertTrue(html, html.contains("'*base*'"))
        assertTrue(html, html.contains("(&lt;unknown&gt;, line 1)"))
        assertFalse(html, html.contains("<em>"))
    }
}
