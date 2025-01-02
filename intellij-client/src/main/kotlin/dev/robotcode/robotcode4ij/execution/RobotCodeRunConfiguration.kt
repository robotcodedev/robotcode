package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.LocatableConfigurationBase
import com.intellij.execution.configurations.RunConfiguration
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.openapi.options.SettingsEditor
import com.intellij.openapi.project.Project

class RobotCodeRunConfiguration(project: Project, factory: ConfigurationFactory) :
    LocatableConfigurationBase<ConfigurationFactory>
        (project, factory, "Robot Framework") {
    override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState {
        return RobotCodeRunProfileState(environment)
    }
    
    override fun getConfigurationEditor(): SettingsEditor<out RunConfiguration> {
        TODO("Not yet implemented")
    }
    
    var suite: String = ""
    var test: String = ""
}
