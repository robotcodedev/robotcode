package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.DataContext
import com.intellij.openapi.actionSystem.impl.SimpleDataContext
import com.intellij.testFramework.TestActionEvent
import com.intellij.testFramework.fixtures.BasePlatformTestCase

class RobotCodeLanguageServerActionsTest : BasePlatformTestCase() {

    fun testRestartActionsAreEnabledOnlyWithAProject() {
        val actions = listOf(
            RobotCodeRestartLanguageServerAction(),
            RobotCodeClearCacheAndRestartLanguageServerAction()
        )
        for (action in actions) {
            val withoutProject = TestActionEvent.createTestEvent(action, DataContext.EMPTY_CONTEXT)
            action.update(withoutProject)
            assertFalse(action.javaClass.simpleName, withoutProject.presentation.isEnabled)

            val withProject = TestActionEvent.createTestEvent(action, SimpleDataContext.getProjectContext(project))
            action.update(withProject)
            assertTrue(action.javaClass.simpleName, withProject.presentation.isEnabled)
        }
    }
}
