package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.ConfigurationTypeBase
import dev.robotcode.robotcode4ij.RobotIcons

class RobotCodeConfigurationType : ConfigurationTypeBase(
    "RobotCodeConfigurationType",
    "Robot Framework",
    "Run Robot Framework tests",
    RobotIcons.RobotCode
) {
    val configurationFactory: RobotCodeRunConfigurationFactory = RobotCodeRunConfigurationFactory(this)
    
    init {
        addFactory(configurationFactory)
    }
    
}
