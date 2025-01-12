package dev.robotcode.robotcode4ij.actions

import com.intellij.ide.actions.CreateFileFromTemplateAction
import com.intellij.ide.actions.CreateFileFromTemplateDialog
import com.intellij.ide.fileTemplates.FileTemplateManager
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiDirectory
import dev.robotcode.robotcode4ij.RobotIcons
import dev.robotcode.robotcode4ij.RobotResourceFileType
import dev.robotcode.robotcode4ij.RobotSuiteFileType

class RobotCreateFileAction : CreateFileFromTemplateAction(
    "Robot Framework File", "Robot Framework file", RobotIcons.Suite
), DumbAware {
    override fun buildDialog(project: Project, directory: PsiDirectory, builder: CreateFileFromTemplateDialog.Builder) {
        builder.setTitle("New Robot Framework File")
        FileTemplateManager.getInstance(project).allTemplates.forEach {
            if (it.extension == RobotSuiteFileType.defaultExtension) {
                builder.addKind(it.name, RobotIcons.Suite, it.name)
            } else if (it.extension == RobotResourceFileType.defaultExtension) {
                builder.addKind(it.name, RobotIcons.Resource, it.name)
            }
        }
        builder.addKind("Suite file", RobotIcons.Suite, "Robot Suite File")
            .addKind("Resource file", RobotIcons.Resource, "Robot Resource File")
        
    }
    
    override fun getActionName(directory: PsiDirectory?, newName: String, templateName: String?): String {
        return "Create Robot Framework File"
    }
}
