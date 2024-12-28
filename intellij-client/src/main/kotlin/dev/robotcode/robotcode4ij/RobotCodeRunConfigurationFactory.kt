package dev.robotcode.robotcode4ij

import com.intellij.execution.configurations.ConfigurationFactory;
import com.intellij.execution.configurations.ConfigurationType
import com.intellij.execution.configurations.RunConfiguration
import com.intellij.openapi.project.Project
import javax.swing.Icon

class RobotCodeRunConfigurationFactory(type: ConfigurationType) : ConfigurationFactory(type) {
    override fun createTemplateConfiguration(project: Project): RunConfiguration {
        TODO("Not yet implemented")
    }
    
    override fun getId(): String {
        return "RobotCode[Default]"
    }
    
    override fun getIcon(): Icon? {
        return RobotIcons.RobotCode;
    }
}
