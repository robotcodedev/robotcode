package dev.robotcode.robotcode4ij.highlighting

import com.intellij.openapi.util.registry.Registry
import com.intellij.psi.tree.IElementType
import dev.robotcode.robotcode4ij.TextMateBundleHolder
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_END
import dev.robotcode.robotcode4ij.psi.RobotTextMateElementType
import dev.robotcode.robotcode4ij.psi.VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.VARIABLE_END
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateElementType
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateHighlightingLexer

class RobotTextMateHighlightingLexer : TextMateHighlightingLexer(
    TextMateBundleHolder.descriptor,
    Registry.get("textmate.line.highlighting.limit").asInteger()
) {
    companion object {
        val BRACES_START = setOf(
            "punctuation.definition.variable.begin.robotframework",
            "punctuation.definition.envvar.begin.robotframework"
        )
        val BRACES_END = setOf(
            "punctuation.definition.variable.end.robotframework",
            "punctuation.definition.envvar.end.robotframework"
        )
    }
    
    override fun getTokenType(): IElementType? {
        val result = super.getTokenType() ?: return null
        if (result is TextMateElementType) {
            return when (result.scope.scopeName) {
                "punctuation.definition.variable.begin.robotframework" -> VARIABLE_BEGIN
                "punctuation.definition.variable.end.robotframework" -> VARIABLE_END
                "punctuation.definition.envvar.begin.robotframework" -> ENVIRONMENT_VARIABLE_BEGIN
                "punctuation.definition.envvar.end.robotframework" -> ENVIRONMENT_VARIABLE_END
                else -> RobotTextMateElementType(result)
            }
        }
        return result
    }
}


