package dev.robotcode.robotcode4ij.highlighting

import com.intellij.lexer.Lexer
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.HighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase
import com.intellij.psi.tree.IElementType
import dev.robotcode.robotcode4ij.psi.ARGUMENT
import dev.robotcode.robotcode4ij.psi.COMMENT_BLOCK
import dev.robotcode.robotcode4ij.psi.COMMENT_LINE
import dev.robotcode.robotcode4ij.psi.CONTINUATION
import dev.robotcode.robotcode4ij.psi.CONTROL_FLOW
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_END
import dev.robotcode.robotcode4ij.psi.ESCAPE
import dev.robotcode.robotcode4ij.psi.EXPRESSION_BEGIN
import dev.robotcode.robotcode4ij.psi.EXPRESSION_END
import dev.robotcode.robotcode4ij.psi.HEADER
import dev.robotcode.robotcode4ij.psi.KEYWORD_CALL
import dev.robotcode.robotcode4ij.psi.KEYWORD_NAME
import dev.robotcode.robotcode4ij.psi.OPERATOR
import dev.robotcode.robotcode4ij.psi.RobotTextMateElementType
import dev.robotcode.robotcode4ij.psi.SETTING
import dev.robotcode.robotcode4ij.psi.TESTCASE_NAME
import dev.robotcode.robotcode4ij.psi.VAR
import dev.robotcode.robotcode4ij.psi.VARIABLE
import dev.robotcode.robotcode4ij.psi.VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.VARIABLE_END
import dev.robotcode.robotcode4ij.psi.VARIABLE_INDEX_BEGIN
import dev.robotcode.robotcode4ij.psi.VARIABLE_INDEX_END


class RobotCodeSyntaxHighlighter : SyntaxHighlighterBase() {
    companion object {
        val elementTypeMap = mapOf(
            COMMENT_LINE to arrayOf(Colors.LINE_COMMENT),
            COMMENT_BLOCK to arrayOf(Colors.BLOCK_COMMENT),
            VARIABLE_BEGIN to arrayOf(Colors.VARIABLE_BEGIN),
            VARIABLE_END to arrayOf(Colors.VARIABLE_END),
            ENVIRONMENT_VARIABLE_BEGIN to arrayOf(Colors.VARIABLE_BEGIN),
            ENVIRONMENT_VARIABLE_END to arrayOf(Colors.VARIABLE_END),
            EXPRESSION_BEGIN to arrayOf(Colors.EXPRESSION_BEGIN),
            EXPRESSION_END to arrayOf(Colors.EXPRESSION_END),
            VARIABLE_INDEX_BEGIN to arrayOf(Colors.VARIABLE_INDEX_BEGIN),
            VARIABLE_INDEX_END to arrayOf(Colors.VARIABLE_INDEX_END),
            TESTCASE_NAME to arrayOf(Colors.TESTCASE_NAME),
            KEYWORD_NAME to arrayOf(Colors.KEYWORD_NAME),
            HEADER to arrayOf(Colors.HEADER),
            SETTING to arrayOf(Colors.SETTING),
            VAR to arrayOf(Colors.VAR),
            KEYWORD_CALL to arrayOf(Colors.KEYWORD_CALL),
            CONTROL_FLOW to arrayOf(Colors.CONTROL_FLOW),
            VARIABLE to arrayOf(Colors.VARIABLE),
            OPERATOR to arrayOf(Colors.OPERATOR),
            ARGUMENT to arrayOf(Colors.ARGUMENT),
            CONTINUATION to arrayOf(Colors.CONTINUATION),
            ESCAPE to arrayOf(Colors.ESCAPE),
        )
        
        val textMateElementMap = mapOf(
            "comment" to arrayOf(DefaultLanguageHighlighterColors.LINE_COMMENT),
            "constant" to arrayOf(DefaultLanguageHighlighterColors.CONSTANT),
            "constant.character.escape" to arrayOf(DefaultLanguageHighlighterColors.VALID_STRING_ESCAPE),
            "constant.language" to arrayOf(DefaultLanguageHighlighterColors.KEYWORD),
            "constant.numeric" to arrayOf(DefaultLanguageHighlighterColors.NUMBER),
            "declaration.section" to arrayOf(DefaultLanguageHighlighterColors.CLASS_NAME),
            "entity.name.section" to arrayOf(DefaultLanguageHighlighterColors.CLASS_NAME),
            "declaration.tag" to arrayOf(DefaultLanguageHighlighterColors.CLASS_NAME),
            "entity.name.function" to arrayOf(DefaultLanguageHighlighterColors.FUNCTION_DECLARATION),
            "entity.name.tag" to arrayOf(DefaultLanguageHighlighterColors.CLASS_NAME),
            "entity.name.type" to arrayOf(DefaultLanguageHighlighterColors.CLASS_NAME),
            "entity.other.attribute-name" to arrayOf(DefaultLanguageHighlighterColors.INSTANCE_FIELD),
            "entity.other.inherited-class" to arrayOf(DefaultLanguageHighlighterColors.CLASS_REFERENCE),
            "invalid" to arrayOf(DefaultLanguageHighlighterColors.INVALID_STRING_ESCAPE),
            "invalid.deprecated.trailing-whitespace" to arrayOf(DefaultLanguageHighlighterColors.INVALID_STRING_ESCAPE),
            "keyword" to arrayOf(DefaultLanguageHighlighterColors.KEYWORD),
            "keyword.control.import" to arrayOf(DefaultLanguageHighlighterColors.KEYWORD),
            "keyword.operator" to arrayOf(DefaultLanguageHighlighterColors.OPERATION_SIGN),
            "markup.heading" to arrayOf(DefaultLanguageHighlighterColors.MARKUP_TAG),
            "markup.list" to arrayOf(DefaultLanguageHighlighterColors.MARKUP_TAG),
            "markup.quote" to arrayOf(DefaultLanguageHighlighterColors.MARKUP_TAG),
            "meta.embedded" to arrayOf(HighlighterColors.TEXT),
            "meta.preprocessor" to arrayOf(DefaultLanguageHighlighterColors.METADATA),
            "meta.section" to arrayOf(DefaultLanguageHighlighterColors.CLASS_NAME),
            "entity.name.section" to arrayOf(DefaultLanguageHighlighterColors.CLASS_NAME),
            "meta.tag" to arrayOf(DefaultLanguageHighlighterColors.METADATA),
            "storage" to arrayOf(DefaultLanguageHighlighterColors.KEYWORD),
            "storage.type.method" to arrayOf(DefaultLanguageHighlighterColors.KEYWORD),
            "string" to arrayOf(DefaultLanguageHighlighterColors.STRING),
            "string.source" to arrayOf(DefaultLanguageHighlighterColors.STRING),
            "string.unquoted" to arrayOf(DefaultLanguageHighlighterColors.STRING),
            "support.class" to arrayOf(DefaultLanguageHighlighterColors.CLASS_REFERENCE),
            "support.constant" to arrayOf(DefaultLanguageHighlighterColors.CONSTANT),
            "support.function" to arrayOf(DefaultLanguageHighlighterColors.FUNCTION_CALL),
            "support.type" to arrayOf(DefaultLanguageHighlighterColors.CLASS_REFERENCE),
            "support.variable" to arrayOf(DefaultLanguageHighlighterColors.GLOBAL_VARIABLE),
            "text" to arrayOf(DefaultLanguageHighlighterColors.STRING),
            "variable" to arrayOf(DefaultLanguageHighlighterColors.GLOBAL_VARIABLE),
            "variable.language" to arrayOf(DefaultLanguageHighlighterColors.GLOBAL_VARIABLE),
            "variable.other" to arrayOf(DefaultLanguageHighlighterColors.GLOBAL_VARIABLE),
            "variable.parameter" to arrayOf(DefaultLanguageHighlighterColors.PARAMETER),
            "punctuation.definition.string" to arrayOf(DefaultLanguageHighlighterColors.STRING),
        )
    }
    
    private val myLexer = RobotCodeLexer()
    
    override fun getHighlightingLexer(): Lexer {
        return myLexer
    }
    
    fun createSubstringSequence(input: String): Sequence<String> = sequence {
        var current = input
        while (current.isNotEmpty()) {
            yield(current)
            current = current.substringBeforeLast('.', "")
        }
    }
    
    override fun getTokenHighlights(tokenType: IElementType?): Array<TextAttributesKey> {
        val result = elementTypeMap[tokenType]
        if (result != null) return result
        
        if (tokenType !is RobotTextMateElementType) return arrayOf(HighlighterColors.TEXT)
        
        val result1 = mutableListOf<TextAttributesKey>()
        
        for (scope1 in (tokenType.scope.scopeName?.toString() ?: "").split(".")) {
            for (scope2 in createSubstringSequence(scope1)) {
                val result2 = textMateElementMap[scope2]
                if (result2 != null) result1.addAll(result2)
            }
        }
        
        if (result1.isNotEmpty()) return result1.toTypedArray()
        
        return arrayOf(HighlighterColors.TEXT)
    }
}

