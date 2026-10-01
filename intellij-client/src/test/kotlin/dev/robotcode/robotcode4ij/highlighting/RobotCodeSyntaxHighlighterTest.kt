package dev.robotcode.robotcode4ij.highlighting

import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.HighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.psi.RobotTextMateElementType
import dev.robotcode.robotcode4ij.psi.VARIABLE_BEGIN
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateScope

class RobotCodeSyntaxHighlighterTest : BasePlatformTestCase() {
    
    private fun highlights(scopeName: String): List<TextAttributesKey> =
        RobotCodeSyntaxHighlighter().getTokenHighlights(RobotTextMateElementType.create(TextMateScope(scopeName, null)))
            .toList()
    
    fun testOperatorInConditionGetsOperatorColor() {
        assertEquals(
            listOf(DefaultLanguageHighlighterColors.OPERATION_SIGN),
            highlights("keyword.operator.comparison.python")
        )
    }
    
    fun testNumberInConditionGetsNumberColor() {
        assertEquals(listOf(DefaultLanguageHighlighterColors.NUMBER), highlights("constant.numeric.dec.python"))
    }
    
    fun testInnermostOfSeveralScopeNamesDecides() {
        assertEquals(
            listOf(DefaultLanguageHighlighterColors.STRING),
            highlights("punctuation.definition.string.begin.python string.quoted.single.python")
        )
    }
    
    fun testScopeWithoutMatchIsPlainText() {
        assertEquals(listOf(HighlighterColors.TEXT), highlights("meta.testcase_setting.documentation.robotframework"))
    }
    
    fun testPythonVariablePrefixIsAVariableBegin() {
        assertSame(VARIABLE_BEGIN, RobotCodeLexer.mapping["punctuation.definition.variable.python.begin.robotframework"])
    }
}
