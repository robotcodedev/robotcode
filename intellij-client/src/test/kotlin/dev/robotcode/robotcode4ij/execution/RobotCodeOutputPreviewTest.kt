package dev.robotcode.robotcode4ij.execution

import com.intellij.openapi.fileEditor.FileEditor
import com.intellij.openapi.fileEditor.FileEditorPolicy
import com.intellij.openapi.fileEditor.FileEditorProvider
import com.intellij.openapi.fileEditor.ex.FileEditorProviderManager
import com.intellij.openapi.fileTypes.impl.AbstractFileType
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.PsiBinaryFile
import com.intellij.psi.PsiManager
import com.intellij.testFramework.LightVirtualFile
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import java.nio.file.Path

class RobotCodeOutputPreviewTest : BasePlatformTestCase() {

    private val report = Path.of("results", "report.html").toAbsolutePath()

    fun testTheProviderTakesOnlyPreviewTabs() {
        val provider = RobotCodeOutputPreviewEditorProvider()

        assertTrue(provider.accept(project, RobotCodeOutputPreviewFile(report)))
        assertFalse(provider.accept(project, LightVirtualFile("report.html", "<html></html>")))
    }

    // the editor manager finds the open tab of a file again through this equality
    fun testPreviewTabsOfOneFileAreEqual() {
        assertEquals(RobotCodeOutputPreviewFile(report), RobotCodeOutputPreviewFile(report))
        assertEquals(RobotCodeOutputPreviewFile(report).hashCode(), RobotCodeOutputPreviewFile(report).hashCode())
        assertFalse(RobotCodeOutputPreviewFile(report) == RobotCodeOutputPreviewFile(report.resolveSibling("log.html")))
    }

    fun testTheFileOfAShownPage() {
        val log = report.resolveSibling("log.html")

        assertEquals(report, pagePath(report.toUri().toString()))
        // a link into the log, and a later load with a query
        assertEquals(log, pagePath(log.toUri().toString() + "#s1-t1"))
        assertEquals(report, pagePath(report.toUri().toString() + "?theme=dark"))
        assertNull(pagePath("http://localhost:63342/project/results/report.html"))
        assertNull(pagePath("about:blank"))
        assertNull(pagePath(null))
    }

    // the pages' prefers-color-scheme, which the preview sets over the browser's DevTools client
    fun testTheColorSchemeOfThePages() {
        assertEquals(
            """{"features":[{"name":"prefers-color-scheme","value":"light"}]}""", colorSchemeParameters(dark = false)
        )
        assertEquals(
            """{"features":[{"name":"prefers-color-scheme","value":"dark"}]}""", colorSchemeParameters(dark = true)
        )
    }

    // LSP4IJ offers language servers for files of a user-defined type and for files whose PSI has the plain text or the
    // TextMate language; a binary PSI has no language
    fun testThePreviewIsNoTextFile() {
        val file = RobotCodeOutputPreviewFile(report)

        assertTrue(file.fileType.isBinary)
        assertFalse(file.fileType is AbstractFileType)
        assertInstanceOf(PsiManager.getInstance(project).findFile(file), PsiBinaryFile::class.java)
    }

    // an editor of another plugin that opens every binary file adds no tab to the preview
    fun testOnlyThePreviewEditorOpensThePreviewFile() {
        val binaryViewer = object : FileEditorProvider, DumbAware {
            override fun accept(project: Project, file: VirtualFile): Boolean = file.fileType.isBinary

            override fun acceptRequiresReadAction(): Boolean = false

            override fun createEditor(project: Project, file: VirtualFile): FileEditor =
                throw UnsupportedOperationException()

            override fun getEditorTypeId(): String = "binary-viewer"

            override fun getPolicy(): FileEditorPolicy = FileEditorPolicy.NONE
        }
        FileEditorProvider.EP_FILE_EDITOR_PROVIDER.point.registerExtension(binaryViewer, testRootDisposable)

        val providers = FileEditorProviderManager.getInstance().getProviderList(project, RobotCodeOutputPreviewFile(report))

        assertEquals(listOf("robotcode-output-preview"), providers.map { it.editorTypeId })
    }

    fun testTheTabLoadsTheFileItself() {
        assertEquals(report.toUri().toString(), RobotCodeOutputPreviewFile(report).pageUrl)
        assertEquals("Preview of report.html", RobotCodeOutputPreviewFile(report).name)
    }
}
