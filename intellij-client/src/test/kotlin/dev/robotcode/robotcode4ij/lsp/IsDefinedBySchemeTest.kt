package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.EditorColorsManager
import com.intellij.openapi.editor.colors.EditorColorsScheme
import com.intellij.openapi.editor.colors.impl.AbstractColorsScheme
import com.intellij.openapi.editor.markup.EffectType
import com.intellij.openapi.editor.markup.TextAttributes
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.highlighting.Colors
import java.awt.Color
import java.awt.Font

class IsDefinedBySchemeTest : BasePlatformTestCase() {
    
    // a copy of the global scheme in which neither the namespace key nor its fallback define anything
    private fun schemeWithUndefinedNamespace(): EditorColorsScheme {
        val scheme = EditorColorsManager.getInstance().globalScheme.clone() as EditorColorsScheme
        scheme.setAttributes(Colors.NAMESPACE, AbstractColorsScheme.INHERITED_ATTRS_MARKER)
        scheme.setAttributes(DefaultLanguageHighlighterColors.CLASS_REFERENCE, AbstractColorsScheme.INHERITED_ATTRS_MARKER)
        return scheme
    }
    
    fun testKeyFallingThroughToIdentifierIsUndefined() {
        assertFalse(isDefinedByScheme(Colors.NAMESPACE, schemeWithUndefinedNamespace()))
    }
    
    fun testStyleWithoutColorIsDefined() {
        val scheme = schemeWithUndefinedNamespace()
        scheme.setAttributes(Colors.NAMESPACE, TextAttributes(null, null, null, null, Font.ITALIC))
        
        assertTrue(isDefinedByScheme(Colors.NAMESPACE, scheme))
    }
    
    fun testColorWithEffectIsDefined() {
        val scheme = schemeWithUndefinedNamespace()
        scheme.setAttributes(
            Colors.NAMESPACE,
            TextAttributes(Color.RED, null, Color.RED, EffectType.LINE_UNDERSCORE, Font.PLAIN)
        )
        
        assertTrue(isDefinedByScheme(Colors.NAMESPACE, scheme))
    }
    
    fun testColorOfTheGeneralCategoryIsDefined() {
        val scheme = schemeWithUndefinedNamespace()
        scheme.setAttributes(
            DefaultLanguageHighlighterColors.CLASS_REFERENCE,
            TextAttributes(Color.BLUE, null, null, null, Font.PLAIN)
        )
        
        assertTrue(isDefinedByScheme(Colors.NAMESPACE, scheme))
    }
}
