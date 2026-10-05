package dev.robotcode.robotcode4ij.highlighting

import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.EditorColorsManager
import com.intellij.testFramework.fixtures.BasePlatformTestCase

class ColorsTest : BasePlatformTestCase() {
    
    private val variableParts = listOf(Colors.VARIABLE_EXPRESSION, Colors.EMBEDDED_ARGUMENT, Colors.PARAMETER)
    
    private val braces = listOf(
        Colors.VARIABLE_BEGIN,
        Colors.VARIABLE_END,
        Colors.EXPRESSION_BEGIN,
        Colors.EXPRESSION_END,
    )
    
    private val brackets = listOf(Colors.VARIABLE_INDEX_BEGIN, Colors.VARIABLE_INDEX_END)
    
    fun testFallbackKeys() {
        assertSame(DefaultLanguageHighlighterColors.FUNCTION_DECLARATION, Colors.KEYWORD_CALL.fallbackAttributeKey)
        assertSame(Colors.KEYWORD_CALL, Colors.KEYWORD_CALL_INNER.fallbackAttributeKey)
        assertSame(Colors.KEYWORD_CALL, Colors.NAME_CALL.fallbackAttributeKey)
        assertSame(DefaultLanguageHighlighterColors.INSTANCE_FIELD, Colors.VARIABLE.fallbackAttributeKey)
        for (key in variableParts) {
            assertSame(key.externalName, Colors.VARIABLE, key.fallbackAttributeKey)
        }
        for (key in braces) {
            assertSame(key.externalName, DefaultLanguageHighlighterColors.BRACES, key.fallbackAttributeKey)
        }
        for (key in brackets) {
            assertSame(key.externalName, DefaultLanguageHighlighterColors.BRACKETS, key.fallbackAttributeKey)
        }
        assertSame(DefaultLanguageHighlighterColors.KEYWORD, Colors.BDD_PREFIX.fallbackAttributeKey)
        assertSame(DefaultLanguageHighlighterColors.CLASS_REFERENCE, Colors.TYPE_HINT.fallbackAttributeKey)
    }
    
    fun testKeysLookLikeTheirFallbackInEveryScheme() {
        val schemes = EditorColorsManager.getInstance().allSchemes.toList()
        assertNotEmpty(schemes)
        for (scheme in schemes) {
            for ((keys, fallback) in listOf(
                variableParts to Colors.VARIABLE,
                braces to DefaultLanguageHighlighterColors.BRACES,
                brackets to DefaultLanguageHighlighterColors.BRACKETS,
            )) {
                for (key in keys) {
                    assertEquals(
                        "${scheme.name}: ${key.externalName}",
                        scheme.getAttributes(fallback),
                        scheme.getAttributes(key)
                    )
                }
            }
        }
    }
}
