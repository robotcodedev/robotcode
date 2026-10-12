package dev.robotcode.robotcode4ij.debugging

import com.intellij.openapi.fileTypes.FileType
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Key
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiFileFactory
import com.intellij.util.LocalTimeCounter
import com.intellij.xdebugger.evaluation.XDebuggerEditorsProviderBase
import dev.robotcode.robotcode4ij.RobotSuiteFileType

/** Marks the Robot Framework files of the debugger's expression editors and console, which the debugger completes. */
internal val DEBUGGER_EXPRESSION_FILE: Key<Boolean> = Key.create("RobotCode.debuggerExpressionFile")

class RobotCodeXDebuggerEditorsProvider : XDebuggerEditorsProviderBase() {
    override fun getFileType(): FileType {
        return RobotSuiteFileType
    }

    // the platform asks for a physical fragment for its editors, which needs the event system
    override fun createExpressionCodeFragment(
        project: Project, text: String, context: PsiElement?, isPhysical: Boolean
    ): PsiFile {
        val fileName = context?.containingFile?.name ?: "dummy.robot"
        return PsiFileFactory.getInstance(project)
            .createFileFromText(fileName, RobotSuiteFileType, text, LocalTimeCounter.currentTime(), isPhysical)
            .also { it.putUserData(DEBUGGER_EXPRESSION_FILE, true) }
    }
}
