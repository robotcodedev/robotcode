package dev.robotcode.robotcode4ij.debugging

import com.intellij.openapi.editor.impl.DocumentImpl
import com.intellij.openapi.util.TextRange
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.lsp.EvaluatableExpression
import org.eclipse.lsp4j.Position
import org.eclipse.lsp4j.Range

class RobotCodeHoverExpressionTest : BasePlatformTestCase() {

    private val document = DocumentImpl("*** Test Cases ***\nGreeting\n    Log    \${message}\n")

    private val variableRange = Range(Position(2, 11), Position(2, 21))

    fun testTheReportedRangeBecomesTheTextRangeOfTheVariable() {
        val info = expressionInfoOf(document, EvaluatableExpression(variableRange, "\${message}"))!!

        val start = document.text.indexOf("\${message}")
        assertEquals(TextRange(start, start + "\${message}".length), info.textRange)
        assertEquals("\${message}", info.expressionText)
    }

    fun testWithoutAnExpressionTheTextInTheRangeIsUsed() {
        val info = expressionInfoOf(document, EvaluatableExpression(variableRange, null))!!

        assertEquals("\${message}", info.expressionText)
    }

    fun testNoReportedExpressionGivesNothing() {
        assertNull(expressionInfoOf(document, null))
        assertNull(expressionInfoOf(document, EvaluatableExpression(null, "\${message}")))
    }
}
