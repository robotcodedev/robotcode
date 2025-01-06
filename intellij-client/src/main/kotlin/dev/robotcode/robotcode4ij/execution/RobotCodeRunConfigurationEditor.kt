package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configuration.EnvironmentVariablesComponent
import com.intellij.util.ui.ComponentWithEmptyText
import com.intellij.ui.RawCommandLineEditor
import com.intellij.openapi.options.SettingsEditor
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.panel
import javax.swing.JComponent

class RobotCodeRunConfigurationEditor : SettingsEditor<RobotCodeRunConfiguration>() {
    
    private val environmentVariablesField = EnvironmentVariablesComponent()
    
    private val argumentsField =
        RawCommandLineEditor().apply {
            if (textField is ComponentWithEmptyText) {
                (textField as ComponentWithEmptyText).emptyText.text =
                    "Additional flags, e.g. --skip-cache, or --parallel=2"
            }
        }
    
    override fun resetEditorFrom(s: RobotCodeRunConfiguration) {
        // TODO("Not yet implemented")
    }
    
    override fun applyEditorTo(s: RobotCodeRunConfiguration) {
        // TODO("Not yet implemented")
    }
    
    override fun createEditor(): JComponent {
        return panel {
            row("&Robot:") {
                textField().label("Suite:")
            }
            row(environmentVariablesField.label) {
                cell(environmentVariablesField.component).align(AlignX.FILL)
            }
            row("A&rguments:") { cell(argumentsField).align(AlignX.FILL) }
        }
    }
    
}
