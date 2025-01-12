package dev.robotcode.robotcode4ij.debugging

import com.intellij.openapi.fileTypes.FileType
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiFileFactory
import com.intellij.xdebugger.evaluation.XDebuggerEditorsProviderBase
import dev.robotcode.robotcode4ij.RobotSuiteFileType

class RobotCodeXDebuggerEditorsProvider : XDebuggerEditorsProviderBase() {
    override fun getFileType(): FileType {
        return RobotSuiteFileType
    }
    
    override fun createExpressionCodeFragment(
        project: Project, text: String, context: PsiElement?, isPhysical: Boolean
    ): PsiFile {
        val fileName = context?.containingFile?.name ?: "dummy.robot"
        return PsiFileFactory.getInstance(project)!!.createFileFromText(
            fileName, RobotSuiteFileType, text
        )
    }
    
}
