package dev.robotcode.robotcode4ij.settings

import com.intellij.application.options.IndentOptionsEditor
import com.intellij.application.options.SmartIndentOptionsEditor
import com.intellij.lang.Language
import com.intellij.psi.codeStyle.CodeStyleSettings
import com.intellij.psi.codeStyle.CodeStyleSettingsCustomizable
import com.intellij.psi.codeStyle.CustomCodeStyleSettings
import com.intellij.psi.codeStyle.LanguageCodeStyleSettingsProvider
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage

class RobotCodeLangCodeStyleSettingsProvider : LanguageCodeStyleSettingsProvider() {
    override fun getLanguage(): Language {
        return RobotFrameworkLanguage
    }
    
    override fun getFileExt(): String {
        return "robot"
    }
    
    override fun getIndentOptionsEditor(): IndentOptionsEditor {
        return SmartIndentOptionsEditor()
    }
    
    override fun createCustomSettings(settings: CodeStyleSettings): CustomCodeStyleSettings {
        return RobotCodeCodeStyleSettings(settings)
    }
    
    override fun customizeSettings(consumer: CodeStyleSettingsCustomizable, settingsType: SettingsType) {
        when (settingsType) {
            SettingsType.INDENT_SETTINGS -> {
                consumer.showAllStandardOptions()
            }
            
            SettingsType.BLANK_LINES_SETTINGS -> {
                // TODO
            }
            
            SettingsType.SPACING_SETTINGS -> {
                // TODO
            }
            
            SettingsType.WRAPPING_AND_BRACES_SETTINGS -> {
                // TODO
            }
            
            SettingsType.COMMENTER_SETTINGS -> {
                // TODO
            }
            
            SettingsType.LANGUAGE_SPECIFIC -> {
                // TODO
            }
        }
    }
    
    override fun getCodeSample(settingsType: SettingsType): String {
        return """
        *** Settings ***
        Library  SeleniumLibrary
        
        *** Variables ***
        ${'$'}{URL}  http://example.com    # a comment
        
        *** Test Cases ***
        Example Test
            Open Application  ${'$'}{URL}
            Log  %{APP_DATA:unknown}
            Close Application
            
        BDD Example Test
            Given application is ppen
            When I enter something into the Search Field
            Then Something Should Happen
            
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
}
