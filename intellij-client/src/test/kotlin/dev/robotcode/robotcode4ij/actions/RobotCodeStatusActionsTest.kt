package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.DataContext
import com.intellij.openapi.actionSystem.impl.SimpleDataContext
import com.intellij.testFramework.TestActionEvent
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration

class RobotCodeStatusActionsTest : BasePlatformTestCase() {

    override fun tearDown() {
        try {
            RobotCodePersonalConfiguration.getInstance(project).disableExtension = false
        } finally {
            super.tearDown()
        }
    }

    private fun presentation(action: AnAction, context: DataContext) =
        TestActionEvent.createTestEvent(action, context).also { action.update(it) }.presentation

    fun testActionsNeedAProject() {
        val projectContext = SimpleDataContext.getProjectContext(project)
        for (action in listOf(RobotCodeConfigurePythonInterpreterAction(), RobotCodeShowLanguageServerLogAction())) {
            assertTrue(presentation(action, projectContext).isEnabled)
            assertFalse(presentation(action, DataContext.EMPTY_CONTEXT).isEnabled)
        }
    }

    fun testEnableActionIsShownOnlyWhileRobotCodeIsSwitchedOff() {
        val context = SimpleDataContext.getProjectContext(project)

        assertFalse(presentation(RobotCodeEnableAction(), context).isVisible)

        RobotCodePersonalConfiguration.getInstance(project).disableExtension = true

        val presentation = presentation(RobotCodeEnableAction(), context)
        assertTrue(presentation.isVisible)
        assertTrue(presentation.isEnabled)
    }
}
