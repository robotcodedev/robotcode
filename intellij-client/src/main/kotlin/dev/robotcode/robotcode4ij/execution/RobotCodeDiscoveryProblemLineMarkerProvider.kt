package dev.robotcode.robotcode4ij.execution

import com.intellij.codeInsight.daemon.LineMarkerInfo
import com.intellij.codeInsight.daemon.LineMarkerProvider
import com.intellij.icons.AllIcons
import com.intellij.openapi.editor.markup.GutterIconRenderer
import com.intellij.psi.PsiElement
import dev.robotcode.robotcode4ij.psi.RobotSuiteFile
import dev.robotcode.robotcode4ij.testing.testManger
import dev.robotcode.robotcode4ij.testing.uri

/**
 * An error icon on line 1 of a suite file that Robot Framework cannot turn into a suite, for example because it has
 * both tests and tasks. Its tooltip shows the problems that discovery reported; it offers no action, because the file
 * cannot run.
 */
class RobotCodeDiscoveryProblemLineMarkerProvider : LineMarkerProvider {
    override fun getLineMarkerInfo(element: PsiElement): LineMarkerInfo<*>? {
        // the first leaf of the file
        if (element.firstChild != null || element.textRange.startOffset != 0) {
            return null
        }
        val file = element.containingFile as? RobotSuiteFile ?: return null
        val uri = file.virtualFile?.uri ?: return null
        val manager = element.project.testManger
        if (manager.findTestItem(uri) != null) {
            return null
        }
        val problems = manager.problems(uri)
        if (problems.isEmpty()) {
            return null
        }
        val tooltip = problems.joinToString("\n")
        return LineMarkerInfo(
            element, element.textRange, AllIcons.General.Error, { tooltip }, null, GutterIconRenderer.Alignment.LEFT
        ) { tooltip }
    }
}
