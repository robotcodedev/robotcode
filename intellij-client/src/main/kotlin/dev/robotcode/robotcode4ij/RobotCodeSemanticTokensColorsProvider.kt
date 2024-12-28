package dev.robotcode.robotcode4ij

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.psi.PsiFile
import com.redhat.devtools.lsp4ij.features.semanticTokens.SemanticTokensColorsProvider


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
            
            "testcaseName" -> RobotColors.TESTCASE_NAME
            "keywordName" -> RobotColors.KEYWORD_NAME
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

