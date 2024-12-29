package dev.robotcode.robotcode4ij

import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.editor.colors.TextAttributesKey.createTextAttributesKey

object RobotColors {
    
    val HEADER: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_HEADER", DefaultLanguageHighlighterColors.KEYWORD)
    
    val TESTCASE_NAME: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_TESTCASE_NAME", DefaultLanguageHighlighterColors.FUNCTION_DECLARATION)
    
    val KEYWORD_NAME: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_KEYWORD_NAME", DefaultLanguageHighlighterColors.FUNCTION_DECLARATION)
    val KEYWORD_CALL: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_KEYWORD_CALL", DefaultLanguageHighlighterColors.FUNCTION_CALL)
    
    val SETTING: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_SETTING", DefaultLanguageHighlighterColors.KEYWORD)
    val SETTING_IMPORT: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_SETTING_IMPORT", DefaultLanguageHighlighterColors.KEYWORD)
    val CONTROL_FLOW: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_CONTROL_FLOW", DefaultLanguageHighlighterColors.KEYWORD)
    
    val EMBEDDED_ARGUMENT: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_EMBEDDED_ARGUMENT", DefaultLanguageHighlighterColors.STRING)
    
    val VARIABLE: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VARIABLE", DefaultLanguageHighlighterColors.GLOBAL_VARIABLE)
    val VARIABLE_EXPRESSION: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VARIABLE_EXPRESSION", DefaultLanguageHighlighterColors.GLOBAL_VARIABLE)
    val VARIABLE_BEGIN: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VARIABLE_BEGIN", DefaultLanguageHighlighterColors.BRACES)
    val VARIABLE_END: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VARIABLE_BEGIN", DefaultLanguageHighlighterColors.BRACES)
    
    val NAMESPACE: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_NAMESPACE", DefaultLanguageHighlighterColors.CLASS_REFERENCE)
    
}

