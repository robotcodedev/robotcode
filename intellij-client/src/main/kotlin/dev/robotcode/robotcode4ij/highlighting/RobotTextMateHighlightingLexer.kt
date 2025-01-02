package dev.robotcode.robotcode4ij.highlighting

import com.intellij.openapi.util.registry.Registry
import com.intellij.psi.tree.IElementType
import dev.robotcode.robotcode4ij.TextMateBundleHolder
import dev.robotcode.robotcode4ij.psi.RobotTextMateElementType
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateElementType
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateHighlightingLexer

class RobotTextMateHighlightingLexer : TextMateHighlightingLexer(
    TextMateBundleHolder.descriptor,
    Registry.get("textmate.line.highlighting.limit").asInteger()
) {
    override fun getTokenType(): IElementType? {
        val result = super.getTokenType() ?: return null
        if (result is TextMateElementType) {
            return RobotTextMateElementType(result)
        }
        return result
    }
}


