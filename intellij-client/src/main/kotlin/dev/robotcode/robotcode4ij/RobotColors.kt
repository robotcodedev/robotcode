package dev.robotcode.robotcode4ij

import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.editor.colors.TextAttributesKey.createTextAttributesKey
import com.intellij.openapi.editor.markup.EffectType
import com.intellij.openapi.editor.markup.TextAttributes

object RobotColors {
    val HEADER: TextAttributesKey =
        createTextAttributesKey(
            "ROBOTFRAMEWORK_HEADER", TextAttributes(
                null, null,
                DefaultLanguageHighlighterColors.KEYWORD
                    .defaultAttributes.foregroundColor,
                EffectType
                    .LINE_UNDERSCORE, 1
            )
        )
    
    val TESTCASE_NAME: TextAttributesKey =
        createTextAttributesKey(
            "ROBOTFRAMEWORK_TESTCASE_NAME", TextAttributes(
                null, null, null,
                null, 1
            )
        )
    
    val KEYWORD_NAME: TextAttributesKey =
        createTextAttributesKey(
            "ROBOTFRAMEWORK_TESTCASE_NAME", TextAttributes(
                null, null, null,
                null, 1
            )
        )
}

