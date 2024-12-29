package dev.robotcode.robotcode4ij

import com.intellij.application.options.CodeStyleAbstractConfigurable
import com.intellij.application.options.CodeStyleAbstractPanel
import com.intellij.application.options.TabbedLanguageCodeStylePanel
import com.intellij.psi.codeStyle.CodeStyleConfigurable
import com.intellij.psi.codeStyle.CodeStyleSettings
import com.intellij.psi.codeStyle.CodeStyleSettingsProvider
import com.intellij.psi.codeStyle.CustomCodeStyleSettings

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
                return GdCodeStyleMainPanel(currentSettings, settings)
            }
        }
    }
    
    private class GdCodeStyleMainPanel(currentSettings: CodeStyleSettings, settings: CodeStyleSettings) :
        TabbedLanguageCodeStylePanel(RobotFrameworkLanguage, currentSettings, settings)
    
}
