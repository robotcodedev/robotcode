package dev.robotcode.robotcode4ij

import com.intellij.application.options.IndentOptionsEditor
import com.intellij.application.options.SmartIndentOptionsEditor
import com.intellij.lang.Language
import com.intellij.psi.codeStyle.CodeStyleSettings
import com.intellij.psi.codeStyle.CodeStyleSettingsCustomizable
import com.intellij.psi.codeStyle.CustomCodeStyleSettings
import com.intellij.psi.codeStyle.LanguageCodeStyleSettingsProvider

class RobotCodeLangCodeStyleSettingsProvider : LanguageCodeStyleSettingsProvider() {
    override fun getLanguage(): Language {
        return RobotFrameworkLanguage
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
        return "*** Settings ***\n" +
            "Library  SeleniumLibrary\n" +
            "\n" +
            "*** Variables ***\n" +
            "${'$'}{BROWSER}  Chrome\n" +
            "\n" +
            "*** Test Cases ***\n" +
            "Open Browser\n" +
            "    Open Browser  https://www.google.com  \${BROWSER}\n" +
            "    Close Browser\n"
    }
}
