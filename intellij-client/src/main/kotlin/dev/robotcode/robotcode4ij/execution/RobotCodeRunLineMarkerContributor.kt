package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.lineMarker.RunLineMarkerContributor
import com.intellij.psi.PsiElement
import com.intellij.util.Urls.newLocalFileUrl
import com.intellij.util.Urls.newUrl
import dev.robotcode.robotcode4ij.testing.testManger

class RobotCodeRunLineMarkerContributor : RunLineMarkerContributor() {
    override fun getInfo(element: PsiElement): Info? {
        var testElement = element.project.testManger.findTestItem(element) ?: return null
        if (testElement.type != "test" && testElement.children.isNullOrEmpty()) {
            return null
        }
        
        val uri = newUrl(
            "robotcode", "/", newLocalFileUrl(testElement.source!!).toString()
        ).addParameters(mapOf("line" to ((testElement.lineno ?: 1) - 1).toString()))
        
        var icon = getTestStateIcon(uri.toString(), element.project, testElement.type != "test")
        return withExecutorActions(icon)
    }
    
    override fun getSlowInfo(element: PsiElement): Info? {
        return super.getSlowInfo(element)
    }
}
