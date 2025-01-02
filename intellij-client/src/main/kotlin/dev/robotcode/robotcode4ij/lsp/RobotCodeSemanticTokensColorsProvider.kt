package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.psi.PsiFile
import com.redhat.devtools.lsp4ij.features.semanticTokens.SemanticTokensColorsProvider
import dev.robotcode.robotcode4ij.highlighting.RobotColors


class RobotCodeSemanticTokensColorsProvider : SemanticTokensColorsProvider {
    
    
    override fun getTextAttributesKey(
        tokenType: String, tokenModifiers: MutableList<String>, file: PsiFile
    ): TextAttributesKey? { // TODO implement RobotCodeSemanticTokensColorsProvider
        return when (tokenType) {
            "header",
            "headerKeyword",
            "headerComment",
            "headerSettings",
            "headerVariable",
            "headerTestcase",
            "headerTask",
                -> RobotColors.HEADER
            
            "setting" -> RobotColors.SETTING
            "settingImport" -> RobotColors.SETTING_IMPORT
            "controlFlow" -> RobotColors.CONTROL_FLOW
            
            "testcaseName" -> RobotColors.TESTCASE_NAME
            "keywordName" -> RobotColors.KEYWORD_NAME
            "keywordCall" -> RobotColors.KEYWORD_CALL
            
            "argument" -> RobotColors.ARGUMENT
            "embeddedArgument" -> RobotColors.EMBEDDED_ARGUMENT
            
            "variable" -> RobotColors.VARIABLE
            "variableExpression" -> RobotColors.VARIABLE_EXPRESSION
            "variableBegin" -> RobotColors.VARIABLE_BEGIN
            "variableEnd" -> RobotColors.VARIABLE_END
            
            "namespace" -> RobotColors.NAMESPACE
            "bddPrefix" -> RobotColors.BDD_PREFIX
            "continuation" -> RobotColors.CONTINUATION
            else -> null
        }
        
        // return when (tokenType) {
        //     "headerTestcase" -> {
        //         val myAttrs = DefaultLanguageHighlighterColors.KEYWORD.defaultAttributes.clone();
        //
        //         myAttrs.effectType = EffectType.LINE_UNDERSCORE;
        //         myAttrs.effectColor = myAttrs.foregroundColor;
        //         myAttrs.fontType = Font.ITALIC;
        //         return TextAttributesKey.createTextAttributesKey(
        //             "tokenType", myAttrs
        //         )
        //     }
    }
}

