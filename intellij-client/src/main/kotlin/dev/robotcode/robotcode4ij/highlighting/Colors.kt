package dev.robotcode.robotcode4ij.highlighting

import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.editor.colors.TextAttributesKey.createTextAttributesKey

object Colors {

    val HEADER: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_HEADER", DefaultLanguageHighlighterColors.KEYWORD)

    val TESTCASE_NAME: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_TESTCASE_NAME", DefaultLanguageHighlighterColors.FUNCTION_DECLARATION)

    val KEYWORD_NAME: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_KEYWORD_NAME", DefaultLanguageHighlighterColors.FUNCTION_DECLARATION)
    val KEYWORD_CALL: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_KEYWORD_CALL", DefaultLanguageHighlighterColors.FUNCTION_CALL)
    val KEYWORD_CALL_INNER: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_KEYWORD_CALL_INNER", DefaultLanguageHighlighterColors.FUNCTION_CALL)
    val NAME_CALL: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_NAME_CALL", DefaultLanguageHighlighterColors.FUNCTION_CALL)

    val SETTING: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_SETTING", DefaultLanguageHighlighterColors.KEYWORD)
    val SETTING_IMPORT: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_SETTING_IMPORT", DefaultLanguageHighlighterColors.KEYWORD)
    val CONTROL_FLOW: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_CONTROL_FLOW", DefaultLanguageHighlighterColors.KEYWORD)

    val VAR: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VAR", DefaultLanguageHighlighterColors.KEYWORD)

    val VARIABLE: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VARIABLE", DefaultLanguageHighlighterColors.GLOBAL_VARIABLE)
    val VARIABLE_EXPRESSION: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VARIABLE_EXPRESSION", DefaultLanguageHighlighterColors.GLOBAL_VARIABLE)

    val VARIABLE_BEGIN: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VARIABLE_BEGIN", DefaultLanguageHighlighterColors.BRACES)
    val VARIABLE_END: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_VARIABLE_END", DefaultLanguageHighlighterColors.BRACES)

    val NAMESPACE: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_NAMESPACE", DefaultLanguageHighlighterColors.CLASS_REFERENCE)

    val ARGUMENT: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_ARGUMENT", DefaultLanguageHighlighterColors.STRING)
    val EMBEDDED_ARGUMENT: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_EMBEDDED_ARGUMENT", DefaultLanguageHighlighterColors.STRING)
    val NAMED_ARGUMENT: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_NAMED_ARGUMENT", DefaultLanguageHighlighterColors.PARAMETER)

    val LINE_COMMENT: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_LINE_COMMENT", DefaultLanguageHighlighterColors.LINE_COMMENT)

    val BLOCK_COMMENT: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_BLOCK_COMMENT", DefaultLanguageHighlighterColors.BLOCK_COMMENT)

    val OPERATOR: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_OPERATOR", DefaultLanguageHighlighterColors.OPERATION_SIGN)

    val BDD_PREFIX: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_BDD_PREFIX", DefaultLanguageHighlighterColors.METADATA)

    val CONTINUATION: TextAttributesKey =
        createTextAttributesKey("ROBOTFRAMEWORK_CONTINUATION", DefaultLanguageHighlighterColors.DOT)
}
