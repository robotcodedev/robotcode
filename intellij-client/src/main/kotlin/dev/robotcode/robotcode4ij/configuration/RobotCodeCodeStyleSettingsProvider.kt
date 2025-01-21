package dev.robotcode.robotcode4ij.configuration

import com.intellij.application.options.CodeStyleAbstractConfigurable
import com.intellij.application.options.CodeStyleAbstractPanel
import com.intellij.application.options.TabbedLanguageCodeStylePanel
import com.intellij.psi.codeStyle.CodeStyleConfigurable
import com.intellij.psi.codeStyle.CodeStyleSettings
import com.intellij.psi.codeStyle.CodeStyleSettingsProvider
import com.intellij.psi.codeStyle.CustomCodeStyleSettings
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage

class RobotCodeCodeStyleSettingsProvider : CodeStyleSettingsProvider() {
    override fun getConfigurableDisplayName() = "Robot Framework"
    
    override fun createCustomSettings(settings: CodeStyleSettings): CustomCodeStyleSettings {
        return RobotCodeCodeStyleSettings(settings)
    }
    
    override fun createConfigurable(
        settings: CodeStyleSettings,
        modelSettings: CodeStyleSettings
    ): CodeStyleConfigurable {
        return object : CodeStyleAbstractConfigurable(settings, modelSettings, this.configurableDisplayName) {
            override fun createPanel(settings: CodeStyleSettings): CodeStyleAbstractPanel {
                return CodeStyleMainPanel(currentSettings, settings)
            }
        }
    }
    
    private class CodeStyleMainPanel(currentSettings: CodeStyleSettings, settings: CodeStyleSettings) :
        TabbedLanguageCodeStylePanel(RobotFrameworkLanguage, currentSettings, settings) {
        override fun initTabs(settings: CodeStyleSettings?) {
            addIndentOptionsTab(settings)
        }
    }
}
