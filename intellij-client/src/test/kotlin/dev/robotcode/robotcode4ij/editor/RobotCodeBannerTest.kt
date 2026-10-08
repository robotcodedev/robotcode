package dev.robotcode.robotcode4ij.editor

import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.ui.EditorNotificationPanel
import com.intellij.ui.InplaceButton
import com.intellij.util.ui.UIUtil
import dev.robotcode.robotcode4ij.EnvironmentResult
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.robotCodeEnvironment

class RobotCodeBannerTest : BasePlatformTestCase() {

    private val environment get() = project.robotCodeEnvironment
    private val notInstalled = EnvironmentState.Checked(EnvironmentResult.RobotNotInstalled)

    override fun setUp() {
        super.setUp()
        environment.resetForTests()
        environment.checks.setState(environment.projectInterpreter, notInstalled)
    }

    override fun tearDown() {
        try {
            EditorNotificationProvider.clearDismissedForTests()
            environment.resetForTests()
        } finally {
            super.tearDown()
        }
    }

    private fun panelFor(): EditorNotificationPanel? {
        val file = myFixture.configureByText("suite.robot", "*** Test Cases ***\nFirst\n    Log    first\n").virtualFile
        val editor = FileEditorManager.getInstance(project).getSelectedEditor(file)!!
        return EditorNotificationProvider().collectNotificationData(project, file)?.apply(editor) as EditorNotificationPanel?
    }

    fun testPipCommandForTheInterpreter() {
        val tooOld = EnvironmentState.Checked(EnvironmentResult.RobotTooOld("4.1"))

        assertEquals("\"/opt/py/bin/python3\" -m pip install robotframework", pipCommand(notInstalled, "/opt/py/bin/python3"))
        assertEquals("\"/opt/py/bin/python3\" -m pip install -U robotframework", pipCommand(tooOld, "/opt/py/bin/python3"))
        assertNull(pipCommand(EnvironmentState.Checked(EnvironmentResult.PythonTooOld("3.9")), "/opt/py/bin/python3"))
        assertNull(pipCommand(notInstalled, null))
    }

    fun testTextShowsThePipCommandOnALineOfItsOwn() {
        val text = bannerText(notInstalled, "/opt/py/bin/python3")

        assertTrue(text, text.startsWith("<html>" + notInstalled.message + "<br>"))
        assertTrue(text, text.endsWith("<code>&quot;/opt/py/bin/python3&quot; -m pip install robotframework</code></html>"))
        assertEquals("<html>" + notInstalled.message + "</html>", bannerText(notInstalled, null))
    }

    fun testPanelOffersTheNextSteps() {
        val panel = panelFor()!!

        for (label in listOf("Configure Python Interpreter...", "Retry", "Disable RobotCode for This Project")) {
            assertNotNull(label, panel.findLabelByName(label))
        }
        assertEquals(bannerText(notInstalled, environment.projectInterpreter.homePath), panel.text)
    }

    fun testClosedBannerStaysHidden() {
        val panel = panelFor()!!

        UIUtil.findComponentOfType(panel, InplaceButton::class.java)!!.doClick()

        assertNull(panelFor())
    }
}
