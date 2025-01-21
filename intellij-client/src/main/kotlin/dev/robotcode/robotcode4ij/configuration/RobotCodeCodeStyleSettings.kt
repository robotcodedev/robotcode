package dev.robotcode.robotcode4ij.configuration

import com.intellij.psi.codeStyle.CodeStyleSettings
import com.intellij.psi.codeStyle.CustomCodeStyleSettings

class RobotCodeCodeStyleSettings(container: CodeStyleSettings) :
    CustomCodeStyleSettings(RobotCodeCodeStyleSettings::class.java.simpleName, container) {
    @JvmField
    var use4SpacesIndentation: Boolean = true
}
