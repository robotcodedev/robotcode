package dev.robotcode.robotcode4ij

import com.intellij.openapi.fileTypes.LanguageFileType
import com.intellij.openapi.fileTypes.OSFileIdeAssociation

object RobotResourceFileType : LanguageFileType(RobotFrameworkLanguage), OSFileIdeAssociation {
    override fun getName() = "ROBOT_FRAMEWORK_RESOURCE"
    override fun getDisplayName() = "Robot Framework Resource"
    override fun getDescription() = "Robot Framework resource files"
    override fun getDefaultExtension() = "robot"
    override fun getIcon() = RobotIcons.Resource
}
