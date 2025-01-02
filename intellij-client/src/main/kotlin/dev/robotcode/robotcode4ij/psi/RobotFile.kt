package dev.robotcode.robotcode4ij.psi

import com.intellij.extapi.psi.PsiFileBase
import com.intellij.openapi.fileTypes.FileType
import com.intellij.psi.FileViewProvider
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import dev.robotcode.robotcode4ij.RobotSuiteFileType

class RobotFile(viewProvider: FileViewProvider) : PsiFileBase(
    viewProvider,
    RobotFrameworkLanguage
) {
    override fun getFileType(): FileType {
        return RobotSuiteFileType
    }
}
