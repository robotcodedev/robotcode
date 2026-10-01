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

private val mapping by lazy {
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

class RobotCodeSemanticTokensColorsProvider : DefaultSemanticTokensColorsProvider() {
    override fun getTextAttributesKey(
        tokenType: String, tokenModifiers: MutableList<String>, file: PsiFile
    ): TextAttributesKey? {
        var tokenTypeAndModifiers = tokenType
        if (tokenModifiers.isNotEmpty()) {
            tokenTypeAndModifiers += ",${tokenModifiers.joinToString(",")}"
        }
        val result = mapping[tokenTypeAndModifiers] ?: mapping[tokenType] ?: super.getTextAttributesKey(
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
        
        // like VS Code: only draw what the color scheme defines, otherwise keep the grammar highlighting
        return if (isDefinedByScheme(result, EditorColorsManager.getInstance().globalScheme)) result else null
    }
}
