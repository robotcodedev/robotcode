package dev.robotcode.robotcode4ij

import com.intellij.openapi.fileTypes.LanguageFileType
import org.jetbrains.plugins.textmate.TextMateBackedFileType

class RobotSuiteFileType() : LanguageFileType(RobotFrameworkLanguage.INSTANCE) {
    override fun getName() = "ROBOT_FRAMEWORK_SUITE";
    override fun getDisplayName() = "Robot Framework Suite";
    override fun getDescription() = "Robot Framework suite files";
    override fun getDefaultExtension() = "robot"
    override fun getIcon() = RobotIcons.Suite
}
