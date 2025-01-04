package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.lineMarker.RunLineMarkerContributor
import com.intellij.icons.AllIcons
import com.intellij.psi.PsiElement
import com.intellij.psi.util.elementType
import dev.robotcode.robotcode4ij.psi.FILE
import dev.robotcode.robotcode4ij.psi.TESTCASE_NAME

class RobotCodeRunLineMarkerContributor : RunLineMarkerContributor() {
    override fun getInfo(element: PsiElement): Info? {
        if (element.elementType != TESTCASE_NAME && element.elementType != FILE) return null
        
        return withExecutorActions(AllIcons.RunConfigurations.TestState.Run)
    }
}
