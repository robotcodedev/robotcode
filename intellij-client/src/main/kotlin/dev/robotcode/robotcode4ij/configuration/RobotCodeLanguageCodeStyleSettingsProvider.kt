package dev.robotcode.robotcode4ij.configuration

import com.intellij.application.options.IndentOptionsEditor
import com.intellij.application.options.SmartIndentOptionsEditor
import com.intellij.lang.Language
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiFileFactory
import com.intellij.psi.codeStyle.CodeStyleSettings
import com.intellij.psi.codeStyle.CommonCodeStyleSettings
import com.intellij.psi.codeStyle.CustomCodeStyleSettings
import com.intellij.psi.codeStyle.LanguageCodeStyleSettingsProvider
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import javax.swing.JCheckBox

class RobotCodeLanguageCodeStyleSettingsProvider : LanguageCodeStyleSettingsProvider() {
    override fun getLanguage(): Language {
        return RobotFrameworkLanguage
    }
    
    override fun getFileExt(): String {
        return "robot"
    }
    
    override fun getIndentOptionsEditor(): IndentOptionsEditor {
        return object : SmartIndentOptionsEditor(this) {
            private lateinit var use4SpacesTabCheckBox: JCheckBox
            
            override fun addComponents() {
                super.addComponents()
                use4SpacesTabCheckBox = JCheckBox("Use 4 spaces indentation")
                @Suppress("removal")
                add(use4SpacesTabCheckBox)
            }
            
            override fun setEnabled(enabled: Boolean) {
                super.setEnabled(enabled)
                use4SpacesTabCheckBox.isEnabled = enabled
            }
            
            override fun isModified(
                settings: CodeStyleSettings,
                options: CommonCodeStyleSettings.IndentOptions
            ): Boolean {
                var result = super.isModified(settings, options)
                val settings = settings.getCustomSettings(RobotCodeCodeStyleSettings::class.java)
                result = result || isFieldModified(use4SpacesTabCheckBox, settings.use4SpacesIndentation)
                return result
            }
            
            override fun apply(settings: CodeStyleSettings, options: CommonCodeStyleSettings.IndentOptions?) {
                super.apply(settings, options)
                settings.getCustomSettings(RobotCodeCodeStyleSettings::class.java).use4SpacesIndentation =
                    use4SpacesTabCheckBox.isSelected
            }
            
            override fun reset(settings: CodeStyleSettings, options: CommonCodeStyleSettings.IndentOptions) {
                super.reset(settings, options)
                val customSettings = settings.getCustomSettings(RobotCodeCodeStyleSettings::class.java)
                use4SpacesTabCheckBox.isSelected = customSettings.use4SpacesIndentation
            }
        }
    }
    
    override fun createCustomSettings(settings: CodeStyleSettings): CustomCodeStyleSettings {
        return RobotCodeCodeStyleSettings(settings)
    }
    
    override fun createFileFromText(project: Project, text: String): PsiFile? {
        return PsiFileFactory.getInstance(project).createFileFromText("dummy.robot", RobotSuiteFileType, text)
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
            Given application is open
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
    
    override fun customizeDefaults(
        commonSettings: CommonCodeStyleSettings,
        indentOptions: CommonCodeStyleSettings.IndentOptions
    ) {
        indentOptions.INDENT_SIZE = 4
        indentOptions.USE_TAB_CHARACTER = false
        indentOptions.CONTINUATION_INDENT_SIZE = 4
    }
}
