package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configuration.EnvironmentVariablesComponent
import com.intellij.openapi.fileChooser.FileChooserDescriptorFactory
import com.intellij.openapi.ui.TextFieldWithBrowseButton
import com.intellij.openapi.options.SettingsEditor
import com.intellij.openapi.project.Project
import com.intellij.ui.RawCommandLineEditor
import com.intellij.ui.dsl.builder.AlignX
import com.intellij.ui.dsl.builder.panel
import com.intellij.util.ui.ComponentWithEmptyText
import javax.swing.JComponent

class RobotCodeRunConfigurationEditor(private val project: Project) : SettingsEditor<RobotCodeRunConfiguration>() {
    
    private val environmentVariablesField = EnvironmentVariablesComponent()
    
    private val variablesField =
        RawCommandLineEditor().apply {
            if (textField is ComponentWithEmptyText) {
                (textField as ComponentWithEmptyText).emptyText.text = "Define variables, e.g. VAR1=value1, VAR2=value2"
            }
        }
    
    private val testSuitePathField = TextFieldWithBrowseButton().apply {
        addBrowseFolderListener(
            project,
            FileChooserDescriptorFactory.createSingleFileDescriptor()
                .withTitle("Select Test Suite")
                .withDescription("Select the path to the test suite")
        )
    }
    
    private val argumentsField =
        RawCommandLineEditor().apply {
            if (textField is ComponentWithEmptyText) {
                (textField as ComponentWithEmptyText).emptyText.text =
                    "Additional flags, e.g. --skip-cache, or --parallel=2"
            }
        }
    
    override fun resetEditorFrom(s: RobotCodeRunConfiguration) {
        // Reset the environment variables field
        environmentVariablesField.envData = s.environmentVariables
        
        // Reset the variables field
        variablesField.text = s.variables ?: ""
        
        // Reset the test suite path field
        testSuitePathField.text = s.testSuitePath ?: ""
        
        // Reset the additional arguments field
        argumentsField.text = s.additionalArguments ?: ""
    }
    
    override fun applyEditorTo(s: RobotCodeRunConfiguration) {
        // Apply the environment variables field
        s.environmentVariables = environmentVariablesField.envData
        
        // Apply the variables field
        s.variables = variablesField.text.ifBlank { null }
        
        // Apply the test suite path field
        s.testSuitePath = testSuitePathField.text.ifBlank { null }
        
        // Apply the additional arguments field
        s.additionalArguments = argumentsField.text.ifBlank { null }
    }
    
    override fun createEditor(): JComponent {
        return panel {
            row("Test Suite Path:") {
                cell(testSuitePathField).align(AlignX.FILL)
            }
            row("Environment Variables:") {
                cell(environmentVariablesField.component).align(AlignX.FILL)
            }
            row("Variables:") {
                cell(variablesField).align(AlignX.FILL)
            }
            row("Additional Arguments:") {
                cell(argumentsField).align(AlignX.FILL)
            }
        }
    }
}
