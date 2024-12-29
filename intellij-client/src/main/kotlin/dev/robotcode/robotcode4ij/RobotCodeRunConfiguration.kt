package dev.robotcode.robotcode4ij


import com.intellij.execution.configurations.ConfigurationTypeBase


class RobotCodeRunConfiguration :
    ConfigurationTypeBase("robotcode", "RobotCode", "Run Robot Framework Tests", RobotIcons.RobotCode) {
    init {
        addFactory(RobotCodeRunConfigurationFactory(this))
    }
}
