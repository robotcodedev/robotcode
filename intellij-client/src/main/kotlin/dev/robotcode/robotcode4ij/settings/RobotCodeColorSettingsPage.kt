package dev.robotcode.robotcode4ij.settings

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.options.colors.AttributesDescriptor
import com.intellij.openapi.options.colors.ColorDescriptor
import com.intellij.openapi.options.colors.ColorSettingsPage
import dev.robotcode.robotcode4ij.RobotIcons
import dev.robotcode.robotcode4ij.highlighting.RobotCodeHighlighter
import dev.robotcode.robotcode4ij.highlighting.RobotColors
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
        AttributesDescriptor("Argument", RobotColors.ARGUMENT),
        AttributesDescriptor("Embedded argument", RobotColors.EMBEDDED_ARGUMENT),
        AttributesDescriptor("Variable", RobotColors.VARIABLE),
        AttributesDescriptor("Variable expression", RobotColors.VARIABLE_EXPRESSION),
        AttributesDescriptor("Variable begin", RobotColors.VARIABLE_BEGIN),
        AttributesDescriptor("Variable end", RobotColors.VARIABLE_END),
        
        AttributesDescriptor("Line comment", RobotColors.LINE_COMMENT),
        AttributesDescriptor("Block comment", RobotColors.BLOCK_COMMENT),
        
        AttributesDescriptor("Operator", RobotColors.OPERATOR),
        AttributesDescriptor("Namespace", RobotColors.NAMESPACE),
        AttributesDescriptor("BDD prefix", RobotColors.BDD_PREFIX),
        
        AttributesDescriptor("Continuation", RobotColors.CONTINUATION),
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
        return RobotCodeHighlighter()
    }
    
    override fun getDemoText(): String {
        return """
        *** Settings ***
        Library  SeleniumLibrary
        
        *** Variables ***
        ${'$'}{URL}  http://example.com    # a comment
        
        *** Test Cases ***
        Example Test
            Open Application  ${'$'}{URL}
            Log  %{APP_DATA=unknown}
            Close Application
            
        BDD Example Test
            Given application is ppen
            When I enter something into the Search Field
            Then Something Should Happen
            
        Another Test
            [Documentation]  This is a test
            ...              with multiple lines
            [Arguments]
            ...    ${'$'}{arg1}
            ...    ${'$'}{arg2}
            
            Log    ${'$'}{arg1} ${'$'}{arg2}
            
        *** Keywords ***
        Open Application
            [Arguments]  ${'$'}{url}
            Open Browser  ${'$'}{url}
            
        Close Application
            Close Browser
            
        *** Comments ***
        this is a comment block
        with multiple lines
        """.trimIndent()
    }
    
    override fun getAdditionalHighlightingTagToDescriptorMap(): MutableMap<String, TextAttributesKey>? {
        return null
    }
}
