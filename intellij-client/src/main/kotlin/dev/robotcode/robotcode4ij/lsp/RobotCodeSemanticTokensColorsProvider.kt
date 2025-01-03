package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.psi.PsiFile
import com.redhat.devtools.lsp4ij.features.semanticTokens.SemanticTokensColorsProvider
import dev.robotcode.robotcode4ij.highlighting.RobotColors

private val mapping by lazy {
    mapOf(
        "header" to RobotColors.HEADER,
        "headerKeyword" to RobotColors.HEADER,
        "headerComment" to RobotColors.HEADER,
        "headerSettings" to RobotColors.HEADER,
        "headerVariable" to RobotColors.HEADER,
        "headerTestcase" to RobotColors.HEADER,
        "headerTask" to RobotColors.HEADER,
        
        "setting" to RobotColors.SETTING,
        "settingImport" to RobotColors.SETTING_IMPORT,
        "controlFlow" to RobotColors.CONTROL_FLOW,
        
        "testcaseName" to RobotColors.TESTCASE_NAME,
        "keywordName" to RobotColors.KEYWORD_NAME,
        "keywordCall" to RobotColors.KEYWORD_CALL,
        
        "argument" to RobotColors.ARGUMENT,
        "embeddedArgument" to RobotColors.EMBEDDED_ARGUMENT,
        
        "variable" to RobotColors.VARIABLE,
        "variableExpression" to RobotColors.VARIABLE_EXPRESSION,
        "variableBegin" to RobotColors.VARIABLE_BEGIN,
        "variableEnd" to RobotColors.VARIABLE_END,
        
        "namespace" to RobotColors.NAMESPACE,
        "bddPrefix" to RobotColors.BDD_PREFIX,
        "continuation" to RobotColors.CONTINUATION
    )
}

class RobotCodeSemanticTokensColorsProvider : SemanticTokensColorsProvider {
    override fun getTextAttributesKey(
        tokenType: String, tokenModifiers: MutableList<String>, file: PsiFile
    ): TextAttributesKey? {
        return mapping[tokenType]
    }
}

