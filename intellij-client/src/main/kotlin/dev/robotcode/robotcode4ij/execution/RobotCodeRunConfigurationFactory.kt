package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.ConfigurationType
import com.intellij.execution.configurations.RunConfiguration
import com.intellij.openapi.project.Project
import dev.robotcode.robotcode4ij.RobotIcons
import javax.swing.Icon

class RobotCodeRunConfigurationFactory(type: ConfigurationType) : ConfigurationFactory(type) {
    override fun createTemplateConfiguration(project: Project): RunConfiguration {
        return RobotCodeRunConfiguration(project, this)
    }
    
    override fun getId(): String {
        return "ROBOT_FRAMEWORK_TEST"
    }
    
    override fun getIcon(): Icon? {
        return RobotIcons.RobotCode
    }
}
