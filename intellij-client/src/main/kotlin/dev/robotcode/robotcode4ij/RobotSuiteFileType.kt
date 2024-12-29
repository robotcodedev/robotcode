package dev.robotcode.robotcode4ij

import com.intellij.openapi.fileTypes.LanguageFileType
import com.intellij.openapi.fileTypes.OSFileIdeAssociation

object RobotSuiteFileType : LanguageFileType(RobotFrameworkLanguage), OSFileIdeAssociation {
    override fun getName() = "ROBOT_FRAMEWORK_SUITE";
    override fun getDisplayName() = "Robot Framework Suite";
    override fun getDescription() = "Robot Framework suite files";
    override fun getDefaultExtension() = "robot"
    override fun getIcon() = RobotIcons.Suite
}
