package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.openapi.actionSystem.DefaultActionGroup
import com.intellij.openapi.actionSystem.Separator
import com.intellij.openapi.actionSystem.impl.SimpleDataContext
import com.intellij.testFramework.TestActionEvent
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.RecordingBrowserLauncher
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration

class RobotCodeShowWhatsNewActionTest : BasePlatformTestCase() {
    companion object {
        private const val GROUP_ID = "dev.robotcode.robotcode4ij.actions"
        private const val ACTION_ID = "dev.robotcode.robotcode4ij.actions.RobotCodeShowWhatsNewAction"
    }

    override fun tearDown() {
        try {
            RobotCodePersonalConfiguration.getInstance(project).disableExtension = false
        } finally {
            super.tearDown()
        }
    }

    // the group is Tools | RobotCode and the menu of the status bar widget
    fun testActionIsTheLastOneOfTheRobotCodeGroup() {
        val actionManager = ActionManager.getInstance()
        val children = (actionManager.getAction(GROUP_ID) as DefaultActionGroup).getChildren(actionManager)

        assertEquals(ACTION_ID, actionManager.getId(children.last()))
        assertTrue(children[children.size - 2] is Separator)
    }

    fun testActionOpensTheNewsAlsoWhileRobotCodeIsSwitchedOff() {
        val browser = RecordingBrowserLauncher.install(testRootDisposable)
        RobotCodePersonalConfiguration.getInstance(project).disableExtension = true
        val action = ActionManager.getInstance().getAction(ACTION_ID)
        val event = TestActionEvent.createTestEvent(action, SimpleDataContext.getProjectContext(project))

        action.update(event)
        assertTrue(event.presentation.isEnabledAndVisible)
        assertEquals("Show What's New", event.presentation.text)

        action.actionPerformed(event)
        assertEquals(listOf("https://robotcode.io/news/latest/"), browser.urls)
    }
}
