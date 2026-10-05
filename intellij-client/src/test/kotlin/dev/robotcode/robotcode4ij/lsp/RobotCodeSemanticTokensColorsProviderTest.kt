package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.EditorColorsManager
import com.intellij.openapi.editor.colors.EditorColorsScheme
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.editor.colors.impl.AbstractColorsScheme
import com.intellij.openapi.editor.markup.TextAttributes
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.highlighting.Colors
import java.awt.Color
import java.awt.Font

class RobotCodeSemanticTokensColorsProviderTest : BasePlatformTestCase() {
    
    // a copy of the global scheme in which none of the keys define anything, so they resolve to plain text
    private fun schemeWithUndefined(vararg keys: TextAttributesKey): EditorColorsScheme {
        val scheme = EditorColorsManager.getInstance().globalScheme.clone() as EditorColorsScheme
        for (key in keys) {
            scheme.setAttributes(key, AbstractColorsScheme.INHERITED_ATTRS_MARKER)
        }
        return scheme
    }
    
    fun testParameterAndTypeHaveRobotFrameworkSettings() {
        assertSame(Colors.PARAMETER, semanticTokenKeys["parameter"])
        assertSame(Colors.TYPE_HINT, semanticTokenKeys["type"])
    }
    
    fun testCorrectingTokensAreDrawnWithPlainText() {
        val scheme = schemeWithUndefined(
            Colors.TYPE_HINT,
            Colors.NAMESPACE,
            DefaultLanguageHighlighterColors.CLASS_REFERENCE,
            Colors.NAMED_ARGUMENT,
            DefaultLanguageHighlighterColors.PARAMETER,
            DefaultLanguageHighlighterColors.OPERATION_SIGN,
        )
        assertFalse(isDefinedByScheme(Colors.TYPE_HINT, scheme))
        
        assertSame(Colors.TYPE_HINT, drawnKey("type", Colors.TYPE_HINT, scheme))
        assertSame(Colors.NAMESPACE, drawnKey("namespace", Colors.NAMESPACE, scheme))
        assertSame(Colors.NAMED_ARGUMENT, drawnKey("namedArgument", Colors.NAMED_ARGUMENT, scheme))
        assertSame(
            DefaultLanguageHighlighterColors.OPERATION_SIGN,
            drawnKey("operator", DefaultLanguageHighlighterColors.OPERATION_SIGN, scheme)
        )
    }
    
    fun testRefiningTokensKeepTheGrammarLookWithPlainText() {
        val scheme = schemeWithUndefined(
            Colors.VARIABLE,
            Colors.PARAMETER,
            DefaultLanguageHighlighterColors.INSTANCE_FIELD,
        )
        
        assertNull(drawnKey("variable", Colors.VARIABLE, scheme))
        assertNull(drawnKey("parameter", Colors.PARAMETER, scheme))
    }
    
    fun testParameterFollowsTheVariableColor() {
        val scheme = schemeWithUndefined(Colors.PARAMETER, DefaultLanguageHighlighterColors.INSTANCE_FIELD)
        scheme.setAttributes(Colors.VARIABLE, TextAttributes(Color.RED, null, null, null, Font.PLAIN))
        
        assertSame(Colors.PARAMETER, drawnKey("parameter", Colors.PARAMETER, scheme))
        assertEquals(Color.RED, scheme.getAttributes(Colors.PARAMETER).foregroundColor)
    }
    
    fun testUnknownTokenTypesAreRefining() {
        val scheme = schemeWithUndefined(DefaultLanguageHighlighterColors.CLASS_REFERENCE)
        
        assertNull(drawnKey("someFutureType", DefaultLanguageHighlighterColors.CLASS_REFERENCE, scheme))
    }
}
