package dev.robotcode.robotcode4ij.settings

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.fileTypes.SyntaxHighlighterFactory
import com.intellij.openapi.options.colors.AttributesDescriptor
import com.intellij.openapi.options.colors.ColorDescriptor
import com.intellij.openapi.options.colors.ColorSettingsPage
import dev.robotcode.robotcode4ij.RobotColors
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import dev.robotcode.robotcode4ij.RobotIcons
import javax.swing.Icon

class RobotCodeColorSettingsPage : ColorSettingsPage {
    
    private val descriptors: Array<AttributesDescriptor> = arrayOf(
        AttributesDescriptor("Header", RobotColors.HEADER),
        AttributesDescriptor("Test case name", RobotColors.TESTCASE_NAME),
        AttributesDescriptor("Keyword name", RobotColors.KEYWORD_NAME),
        AttributesDescriptor("Keyword call", RobotColors.KEYWORD_CALL),
        AttributesDescriptor("Setting", RobotColors.SETTING),
        AttributesDescriptor("Setting import", RobotColors.SETTING_IMPORT),
        AttributesDescriptor("Control flow", RobotColors.CONTROL_FLOW),
        AttributesDescriptor("Embedded argument", RobotColors.EMBEDDED_ARGUMENT),
        AttributesDescriptor("Variable", RobotColors.VARIABLE),
        AttributesDescriptor("Variable expression", RobotColors.VARIABLE_EXPRESSION),
        AttributesDescriptor("Variable begin", RobotColors.VARIABLE_BEGIN),
        AttributesDescriptor("Variable end", RobotColors.VARIABLE_END),
    )
    
    override fun getAttributeDescriptors(): Array<AttributesDescriptor> {
        return descriptors
    }
    
    override fun getColorDescriptors(): Array<ColorDescriptor> {
        return ColorDescriptor.EMPTY_ARRAY
    }
    
    override fun getDisplayName(): String {
        return "Robot Framework"
    }
    
    override fun getIcon(): Icon? {
        return RobotIcons.RobotCode
    }
    
    override fun getHighlighter(): SyntaxHighlighter {
        return SyntaxHighlighterFactory.getSyntaxHighlighter(RobotFrameworkLanguage, null, null)
    }
    
    override fun getDemoText(): String {
        return """
            *** Settings ***
            Library  SeleniumLibrary
            
            *** Variables ***
            ${'$'}{URL}  http://example.com
            
            *** Test Cases ***
            Example Test
                Open Browser  ${'$'}{URL}
                Close Browser
        """.trimIndent()
    }
    
    override fun getAdditionalHighlightingTagToDescriptorMap(): MutableMap<String, TextAttributesKey>? {
        return null
    }
}
