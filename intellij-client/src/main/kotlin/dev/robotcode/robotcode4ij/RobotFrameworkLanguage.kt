package dev.robotcode.robotcode4ij

import com.intellij.lang.Language

class RobotFrameworkLanguage : Language("robotframework") {
    companion object {
        val INSTANCE = RobotFrameworkLanguage();
    }

    override fun getDisplayName() = "Robot Framework"
}