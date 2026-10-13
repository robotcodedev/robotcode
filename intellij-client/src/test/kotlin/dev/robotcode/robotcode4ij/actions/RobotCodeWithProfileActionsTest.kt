package dev.robotcode.robotcode4ij.actions

import com.intellij.execution.lineMarker.ExecutorAction
import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.testFramework.fixtures.BasePlatformTestCase

class RobotCodeWithProfileActionsTest : BasePlatformTestCase() {

    private val manager get() = ActionManager.getInstance()

    private fun ids(actions: List<AnAction>) = actions.map { manager.getId(it) }

    // the platform puts its extra actions, such as "Modify Run Configuration...", after the executor actions
    fun testProfileActionsComeRightAfterTheExecutorActions() {
        val gutter = ExecutorAction.getActions(1)
        val executors = gutter.indexOfLast { it is ExecutorAction } + 1
        assertTrue(executors > 0)

        val actions = withProfileActions(gutter).toList()

        assertEquals(gutter.take(executors), actions.take(executors))
        assertEquals(
            listOf(RUN_WITH_PROFILE_ACTION_ID, DEBUG_WITH_PROFILE_ACTION_ID), ids(actions.subList(executors, executors + 2))
        )
        assertEquals(gutter.drop(executors), actions.drop(executors + 2))
    }

    fun testWithoutExecutorActionsTheProfileActionsComeLast() {
        val actions = withProfileActions(arrayOf(manager.getAction("CreateRunConfiguration"))).toList()

        assertEquals(listOf("CreateRunConfiguration", RUN_WITH_PROFILE_ACTION_ID, DEBUG_WITH_PROFILE_ACTION_ID), ids(actions))
    }
}
