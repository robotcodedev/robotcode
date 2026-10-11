package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Location
import com.intellij.execution.PsiLocation
import com.intellij.execution.testframework.sm.runner.SMTestLocator
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.ModificationTracker
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiManager
import com.intellij.psi.search.GlobalSearchScope
import com.intellij.util.Urls
import dev.robotcode.robotcode4ij.testing.testManger
import dev.robotcode.robotcode4ij.testing.uri

/**
 * The element of a result: the file for line 0, which only suites get, and for a line beyond the end of the edited
 * file, else the leaf at the start of the line.
 */
private fun elementAt(file: PsiFile, line: Int?): PsiElement {
    if (line == null || line <= 0) {
        return file
    }
    val document = PsiDocumentManager.getInstance(file.project).getDocument(file) ?: return file
    if (line >= document.lineCount) {
        return file
    }
    return file.findElementAt(document.getLineStartOffset(line)) ?: file
}

/**
 * The line on which discovery now sees the test or task with the full name [longname] in [file]. A result keeps the
 * line of its run, so after lines were added or removed above a test, only its name finds it again.
 */
private fun currentLine(project: Project, file: VirtualFile, longname: String?): Int? {
    longname ?: return null
    val suite = project.testManger.findTestItem(file.uri) ?: return null
    return suite.children?.firstOrNull { it.longname == longname }?.range?.start?.line?.toInt()
}

// reads files, documents and the discovery result, not the indexes, so results keep Run and Jump to Source while the
// IDE indexes
class RobotSMTestLocator : SMTestLocator, DumbAware {
    override fun getLocation(
        protocol: String, path: String, project: Project, scope: GlobalSearchScope
    ): MutableList<Location<PsiElement>> = getLocation(protocol, path, null, project, scope)

    // the metainfo of a result is the full name of its test, task or suite
    override fun getLocation(
        protocol: String, path: String, metainfo: String?, project: Project, scope: GlobalSearchScope
    ): MutableList<Location<PsiElement>> {

        val uri = Urls.parse("file://$path", true) ?: return mutableListOf()
        val line = uri.parameters?.drop(1)?.split("&")?.firstOrNull { it.startsWith("line=") }?.substring(5)
            ?.toIntOrNull()
        val virtualFile = LocalFileSystem.getInstance().findFileByPath(uri.path) ?: return mutableListOf()

        // folder suites carry their folder as source
        val psiManager = PsiManager.getInstance(project)
        val element = if (virtualFile.isDirectory) {
            psiManager.findDirectory(virtualFile)
        } else {
            psiManager.findFile(virtualFile)?.let { elementAt(it, currentLine(project, virtualFile, metainfo) ?: line) }
        } ?: return mutableListOf()
        return mutableListOf(PsiLocation(element))
    }

    // the location also depends on the discovery result, which changes after an edit without changing the PSI
    override fun getLocationCacheModificationTracker(project: Project): ModificationTracker =
        ModificationTracker.EVER_CHANGED

}
