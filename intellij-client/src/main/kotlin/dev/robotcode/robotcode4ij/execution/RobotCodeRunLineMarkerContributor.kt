package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.lineMarker.RunLineMarkerContributor
import com.intellij.icons.AllIcons
import com.intellij.psi.PsiElement
import dev.robotcode.robotcode4ij.testing.testManger

class RobotCodeRunLineMarkerContributor : RunLineMarkerContributor() {
    override fun getInfo(element: PsiElement): Info? {
        var testElement = element.project.testManger.findTestItem(element) ?: return null
        var icon = AllIcons.RunConfigurations.TestState.Run
        if (testElement.type == "suite") {
            icon = AllIcons.RunConfigurations.TestState.Run_run
        }
        return withExecutorActions(icon)
    }
    
    override fun getSlowInfo(element: PsiElement): Info? {
        return super.getSlowInfo(element)
    }
}
