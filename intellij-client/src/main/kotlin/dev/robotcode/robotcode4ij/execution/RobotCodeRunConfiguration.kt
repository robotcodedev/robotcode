package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.configuration.EnvironmentVariablesData
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.LocatableConfigurationBase
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.testframework.sm.runner.SMRunnerConsolePropertiesProvider
import com.intellij.execution.testframework.sm.runner.SMTRunnerConsoleProperties
import com.intellij.openapi.options.SettingsEditor
import com.intellij.openapi.project.Project
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import org.jdom.Element

class RobotCodeRunConfiguration(project: Project, factory: ConfigurationFactory) :
    LocatableConfigurationBase<ConfigurationFactory>
        (project, factory, "Robot Framework"), SMRunnerConsolePropertiesProvider {
    
    // Environment variables
    var environmentVariables: EnvironmentVariablesData = EnvironmentVariablesData.DEFAULT
    
    // Variables
    var variables: String? = null
    
    // Test suite path
    var testSuitePath: String? = null
    
    // Additional arguments
    var additionalArguments: String? = null
    
    var includedTestItems: String? = null
    
    override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState {
        return RobotCodeRunProfileState(this, environment)
    }
    
    override fun createTestConsoleProperties(executor: Executor): SMTRunnerConsoleProperties {
        return RobotRunnerConsoleProperties(this, "Robot Framework", executor)
    }
    
    override fun getConfigurationEditor(): SettingsEditor<out RobotCodeRunConfiguration> {
        return RobotCodeRunConfigurationEditor(project)
    }
    
    override fun writeExternal(element: Element) {
        super.writeExternal(element)
        // Save data to XML
        environmentVariables.writeExternal(element)
        element.setAttribute("testitems", includedTestItems ?: "")
        element.setAttribute("variables", variables ?: "")
        element.setAttribute("testSuitePath", testSuitePath ?: "")
        element.setAttribute("additionalArguments", additionalArguments ?: "")
    }
    
    override fun readExternal(element: Element) {
        super.readExternal(element)
        // Read data from XML
        environmentVariables = EnvironmentVariablesData.readExternal(element)
        variables = element.getAttributeValue("variables")
        testSuitePath = element.getAttributeValue("testSuitePath")
        additionalArguments = element.getAttributeValue("additionalArguments")
        includedTestItems = element.getAttributeValue("testitems")
    }
}
