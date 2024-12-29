package dev.robotcode.robotcode4ij

import com.intellij.lang.Language

object RobotFrameworkLanguage : Language("robotframework") {
    private fun readResolve(): Any = RobotFrameworkLanguage
    override fun getDisplayName() = "Robot Framework"
}
