package dev.robotcode.robotcode4ij.execution

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

    fun testTheTabLoadsTheFileItself() {
        assertEquals(report.toUri().toString(), RobotCodeOutputPreviewFile(report).pageUrl)
        assertEquals("Preview of report.html", RobotCodeOutputPreviewFile(report).name)
    }
}
