package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.options.colors.AttributesDescriptor
import com.intellij.openapi.options.colors.ColorDescriptor
import com.intellij.openapi.options.colors.ColorSettingsPage
import dev.robotcode.robotcode4ij.RobotIcons
import dev.robotcode.robotcode4ij.highlighting.Colors
import dev.robotcode.robotcode4ij.highlighting.RobotCodeSyntaxHighlighter
import javax.swing.Icon

class RobotCodeColorSettingsPage : ColorSettingsPage {

    private val descriptors: Array<AttributesDescriptor> = arrayOf(
        AttributesDescriptor("Header", Colors.HEADER),
        AttributesDescriptor("Test case name", Colors.TESTCASE_NAME),
        AttributesDescriptor("Keyword name", Colors.KEYWORD_NAME),
        AttributesDescriptor("Keyword call", Colors.KEYWORD_CALL),
        AttributesDescriptor("Keyword call inner", Colors.KEYWORD_CALL_INNER),
        AttributesDescriptor("Name call", Colors.NAME_CALL),
        AttributesDescriptor("Setting", Colors.SETTING),
        AttributesDescriptor("Setting import", Colors.SETTING_IMPORT),
        AttributesDescriptor("Control flow", Colors.CONTROL_FLOW),
        AttributesDescriptor("Var statement", Colors.VAR),
        AttributesDescriptor("Argument", Colors.ARGUMENT),
        AttributesDescriptor("Embedded argument", Colors.EMBEDDED_ARGUMENT),
        AttributesDescriptor("Named argument", Colors.NAMED_ARGUMENT),
        AttributesDescriptor("Variable", Colors.VARIABLE),
        AttributesDescriptor("Variable expression", Colors.VARIABLE_EXPRESSION),
        AttributesDescriptor("Variable begin", Colors.VARIABLE_BEGIN),
        AttributesDescriptor("Variable end", Colors.VARIABLE_END),

        AttributesDescriptor("Line comment", Colors.LINE_COMMENT),
        AttributesDescriptor("Block comment", Colors.BLOCK_COMMENT),

        AttributesDescriptor("Operator", Colors.OPERATOR),
        AttributesDescriptor("Namespace", Colors.NAMESPACE),
        AttributesDescriptor("BDD prefix", Colors.BDD_PREFIX),

        AttributesDescriptor("Continuation", Colors.CONTINUATION),
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
        return RobotCodeSyntaxHighlighter()
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
            Do Something with   argument1   argument2
            ...    argument3
            # This is a comment
            ...    argument4
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
            [Tags]  example
            [Setup]  Open Application  with arguments

            Log    ${'$'}{arg1} ${'$'}{arg2}
            Log To Console  Hello World

        *** Keywords ***
        Open Application
            [Arguments]  ${'$'}{url}
            Open Browser  ${'$'}{url}

        Close Application
            Close Browser


        Do Something Different
            [Arguments]  ${'$'}{arg1}  ${'$'}{arg2}
            IF  ${'$'}arg1=="value"
                Log  ${'$'}{arg1}
            ELSE
                Log  ${'$'}{arg2}
            END

            IF  ${'$'}arg2==1234
                Log  ${'$'}{arg1}
            ELSE IF  ${'$'}arg2==789
                Log  ${'$'}{arg2}
            END

        *** Comments ***
        this is a comment block
        with multiple lines
        """.trimIndent()
    }

    override fun getAdditionalHighlightingTagToDescriptorMap(): MutableMap<String, TextAttributesKey>? {
        return null
    }
}
