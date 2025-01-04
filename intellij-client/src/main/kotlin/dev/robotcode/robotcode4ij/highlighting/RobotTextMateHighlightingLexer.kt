package dev.robotcode.robotcode4ij.highlighting

import com.intellij.openapi.util.registry.Registry
import com.intellij.psi.tree.IElementType
import dev.robotcode.robotcode4ij.TextMateBundleHolder
import dev.robotcode.robotcode4ij.psi.ARGUMENT
import dev.robotcode.robotcode4ij.psi.COMMENT_BLOCK
import dev.robotcode.robotcode4ij.psi.COMMENT_LINE
import dev.robotcode.robotcode4ij.psi.CONTINUATION
import dev.robotcode.robotcode4ij.psi.CONTROL_FLOW
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_END
import dev.robotcode.robotcode4ij.psi.HEADER
import dev.robotcode.robotcode4ij.psi.KEYWORD_CALL
import dev.robotcode.robotcode4ij.psi.KEYWORD_NAME
import dev.robotcode.robotcode4ij.psi.OPERATOR
import dev.robotcode.robotcode4ij.psi.RobotTextMateElementType
import dev.robotcode.robotcode4ij.psi.SETTING
import dev.robotcode.robotcode4ij.psi.TESTCASE_NAME
import dev.robotcode.robotcode4ij.psi.VARIABLE
import dev.robotcode.robotcode4ij.psi.VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.VARIABLE_END
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateElementType
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateHighlightingLexer

class RobotTextMateHighlightingLexer : TextMateHighlightingLexer(
    TextMateBundleHolder.descriptor, Registry.get("textmate.line.highlighting.limit").asInteger()
) {
    companion object {
        val mapping by lazy {
            mapOf(
                "comment.line.robotframework" to COMMENT_LINE,
                "comment.line.rest.robotframework" to COMMENT_LINE,
                "comment.block.robotframework" to COMMENT_BLOCK,
                "punctuation.definition.variable.begin.robotframework" to VARIABLE_BEGIN,
                "punctuation.definition.variable.end.robotframework" to VARIABLE_END,
                "punctuation.definition.envvar.begin.robotframework" to ENVIRONMENT_VARIABLE_BEGIN,
                "punctuation.definition.envvar.end.robotframework" to ENVIRONMENT_VARIABLE_END,
                
                "entity.name.function.testcase.name.robotframework" to TESTCASE_NAME,
                "entity.name.function.keyword.name.robotframework" to KEYWORD_NAME,
                
                "keyword.other.header.robotframework" to HEADER,
                "keyword.other.header.settings.robotframework" to HEADER,
                "keyword.other.header.variable.robotframework" to HEADER,
                "keyword.other.header.testcase.robotframework" to HEADER,
                "keyword.other.header.task.robotframework" to HEADER,
                "keyword.other.header.keyword.robotframework" to HEADER,
                "keyword.other.header.comment.robotframework" to HEADER,
                
                "keyword.control.settings.robotframework" to SETTING,
                "keyword.control.settings.documentation.robotframework" to SETTING,
                
                "entity.name.function.keyword-call.robotframework" to KEYWORD_CALL,
                "keyword.control.flow.robotframework" to CONTROL_FLOW,
                
                "keyword.other.robotframework" to SETTING,
                
                "variable.name.readwrite.robotframework" to VARIABLE,
                "keyword.operator.robotframework" to OPERATOR,
                
                "constant.character.robotframework" to ARGUMENT,
                "string.unquoted.argument.robotframework" to ARGUMENT,
                
                "keyword.operator.continue.robotframework" to CONTINUATION,
            )
        }
    }
    
    override fun getTokenType(): IElementType? {
        val result = super.getTokenType() ?: return null
        if (result is TextMateElementType) {
            return mapping[result.scope.scopeName] ?: RobotTextMateElementType(result)
        }
        return result
    }
}


