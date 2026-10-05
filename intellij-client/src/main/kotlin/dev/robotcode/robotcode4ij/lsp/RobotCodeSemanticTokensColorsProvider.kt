package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.HighlighterColors
import com.intellij.openapi.editor.colors.EditorColorsManager
import com.intellij.openapi.editor.colors.EditorColorsScheme
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.psi.PsiFile
import com.redhat.devtools.lsp4ij.features.semanticTokens.DefaultSemanticTokensColorsProvider
import dev.robotcode.robotcode4ij.highlighting.Colors
import java.util.concurrent.ConcurrentHashMap

internal val semanticTokenKeys by lazy {
    mapOf(
        "header" to Colors.HEADER,
        "headerKeyword" to Colors.HEADER,
        "headerComment" to Colors.HEADER,
        "headerSettings" to Colors.HEADER,
        "headerVariable" to Colors.HEADER,
        "headerTestcase" to Colors.HEADER,
        "headerTask" to Colors.HEADER,
        
        "setting" to Colors.SETTING,
        "settingImport" to Colors.SETTING_IMPORT,
        "controlFlow" to Colors.CONTROL_FLOW,
        "forSeparator" to Colors.CONTROL_FLOW,
        "var" to Colors.VAR,
        
        "testcaseName" to Colors.TESTCASE_NAME,
        "keywordName" to Colors.KEYWORD_NAME,
        "keywordCall" to Colors.KEYWORD_CALL,
        "keywordCallInner" to Colors.KEYWORD_CALL_INNER,
        "nameCall" to Colors.NAME_CALL,
        "argument" to Colors.ARGUMENT,
        "namedArgument" to Colors.NAMED_ARGUMENT,
        "parameter" to Colors.PARAMETER,
        "type" to Colors.TYPE_HINT,
        "variable" to Colors.VARIABLE,
        "variable,embedded" to Colors.EMBEDDED_ARGUMENT,
        "variableExpression" to Colors.VARIABLE_EXPRESSION,
        "variableBegin" to Colors.VARIABLE_BEGIN,
        "variableEnd" to Colors.VARIABLE_END,
        "expressionBegin" to Colors.EXPRESSION_BEGIN,
        "expressionEnd" to Colors.EXPRESSION_END,
        "namespace" to Colors.NAMESPACE,
        "bddPrefix" to Colors.BDD_PREFIX,
        "continuation" to Colors.CONTINUATION,
        "escape" to Colors.ESCAPE,
        "config" to Colors.LINE_COMMENT,
        "error" to Colors.ERROR,
    )
}

/**
 * Token types that correct what the grammar shows at their place, for example a type hint that the grammar shows as
 * part of the variable name. They are drawn even when their key looks like plain text, because the grammar look
 * belongs to another category there. All other token types only refine the grammar look.
 */
internal val correctingTokenTypes = setOf(
    "type",
    "namedArgument",
    "namespace",
    "operator",
    "keywordCall",
    "keywordCallInner",
    "nameCall",
    "argument",
    "bddPrefix",
    "controlFlow",
    "error",
)

private val reportedUnknownTokenTypes = ConcurrentHashMap.newKeySet<String>()

/**
 * Returns whether [scheme] defines anything for [key], directly or through one of its fallback keys.
 * A key that only resolves to the plain text attributes would paint plain text over the grammar highlighting.
 */
internal fun isDefinedByScheme(key: TextAttributesKey, scheme: EditorColorsScheme): Boolean {
    val attributes = scheme.getAttributes(key) ?: return false
    if (attributes.isEmpty) return false
    
    return attributes != scheme.getAttributes(DefaultLanguageHighlighterColors.IDENTIFIER)
        && attributes != scheme.getAttributes(HighlighterColors.TEXT)
}

/**
 * Returns [key] if a token of [tokenType] is drawn with it in [scheme]: a correcting token always, a refining token
 * only when the scheme defines something for its key. Otherwise the token keeps the grammar highlighting.
 */
internal fun drawnKey(tokenType: String, key: TextAttributesKey, scheme: EditorColorsScheme): TextAttributesKey? {
    return if (tokenType in correctingTokenTypes || isDefinedByScheme(key, scheme)) key else null
}

class RobotCodeSemanticTokensColorsProvider : DefaultSemanticTokensColorsProvider() {
    override fun getTextAttributesKey(
        tokenType: String, tokenModifiers: MutableList<String>, file: PsiFile
    ): TextAttributesKey? {
        var tokenTypeAndModifiers = tokenType
        if (tokenModifiers.isNotEmpty()) {
            tokenTypeAndModifiers += ",${tokenModifiers.joinToString(",")}"
        }
        val result = semanticTokenKeys[tokenTypeAndModifiers] ?: semanticTokenKeys[tokenType] ?: super.getTextAttributesKey(
            tokenType,
            tokenModifiers,
            file
        )
        
        if (result == null) {
            if (reportedUnknownTokenTypes.add(tokenType)) {
                thisLogger().warn("Unknown token type: $tokenType")
            }
            return null
        }
        
        return drawnKey(tokenType, result, EditorColorsManager.getInstance().globalScheme)
    }
}
