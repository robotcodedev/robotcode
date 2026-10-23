package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.ExecutorRegistry
import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.lineMarker.ExecutorAction
import com.intellij.execution.lineMarker.RunLineMarkerContributor
import com.intellij.icons.AllIcons
import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.wm.ToolWindowId
import com.intellij.psi.PsiDocumentManager
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.actions.DEBUG_WITH_PROFILE_ACTION_ID
import dev.robotcode.robotcode4ij.actions.RUN_WITH_PROFILE_ACTION_ID
import dev.robotcode.robotcode4ij.testing.Position
import dev.robotcode.robotcode4ij.testing.Range
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.testManger
import dev.robotcode.robotcode4ij.testing.uri
import javax.swing.Icon

private const val OTHER_EXECUTOR_ID = "dev.robotcode.robotcode4ij.test.OtherExecutor"

// an executor besides Run and Debug, as PyCharm Professional's profiler group is one; the platform registers its
// context action, so that the gutter offers it
private class OtherExecutor : Executor() {
    override fun getToolWindowId(): String = ToolWindowId.RUN
    override fun getToolWindowIcon(): Icon = AllIcons.Actions.Execute
    override fun getIcon(): Icon = AllIcons.Actions.Execute
    override fun getDisabledIcon(): Icon? = null
    override fun getDescription(): String = "Runs with another tool"
    override fun getActionName(): String = "Other"
    override fun getId(): String = OTHER_EXECUTOR_ID
    override fun getStartActionText(): String = "Run with Other"
    override fun getContextActionId(): String = "$OTHER_EXECUTOR_ID.context"
    override fun getHelpId(): String? = null
}

class RobotCodeRunMarkerExecutorsTest : BasePlatformTestCase() {

    override fun setUp() {
        super.setUp()
        // the registry adds the context action of an executor that is registered later
        ExecutorRegistry.getInstance()
        Executor.EXECUTOR_EXTENSION_NAME.point.registerExtension(OtherExecutor(), testRootDisposable)
    }

    override fun tearDown() {
        try {
            project.testManger.setTestItemsForTests(arrayOf())
        } finally {
            super.tearDown()
        }
    }

    // a test "First" on the second line of a suite file
    private fun suiteWithOneTest() {
        val file = myFixture.configureByText("suite.robot", "*** Test Cases ***\nFirst\n    Log    first\n").virtualFile
        val test = RobotCodeTestItem(
            type = "test", id = "suite.First", name = "First", longname = "Suite.First", lineno = 2,
            uri = file.uri, source = file.path, range = Range(Position(1u, 0u), Position(1u, 5u))
        )
        val suite = RobotCodeTestItem(
            type = "suite", id = "suite", name = "Suite", longname = "Suite", uri = file.uri, source = file.path,
            children = arrayOf(test)
        )
        project.testManger.setTestItemsForTests(arrayOf(suite))
    }

    private fun executorIds(actions: Array<AnAction>) = actions.filterIsInstance<ExecutorAction>().map { it.executor.id }

    private fun assertOnlyRunAndDebugAmongTheExecutors(info: RunLineMarkerContributor.Info?) {
        val gutter = ExecutorAction.getActions(1)
        assertTrue(OTHER_EXECUTOR_ID in executorIds(gutter))

        val actions = info!!.actions
        val manager = ActionManager.getInstance()
        val extras = gutter.filter { it !is ExecutorAction }

        assertEquals(listOf(DefaultRunExecutor.EXECUTOR_ID, DefaultDebugExecutor.EXECUTOR_ID), executorIds(actions))
        assertEquals(listOf(RUN_WITH_PROFILE_ACTION_ID, DEBUG_WITH_PROFILE_ACTION_ID), actions.drop(2).take(2).map {
            manager.getId(it)
        })
        assertEquals(extras, actions.drop(4))
    }

    fun testTheRunMarkerOfATestOffersOnlyRunAndDebugAmongTheExecutors() {
        suiteWithOneTest()
        val document = PsiDocumentManager.getInstance(project).getDocument(myFixture.file)!!
        val testName = myFixture.file.findElementAt(document.getLineStartOffset(1))!!

        assertOnlyRunAndDebugAmongTheExecutors(RobotCodeRunLineMarkerContributor().getInfo(testName))
    }

    fun testTheRunMarkerOfASuiteOffersOnlyRunAndDebugAmongTheExecutors() {
        suiteWithOneTest()

        assertOnlyRunAndDebugAmongTheExecutors(RobotCodeRunLineMarkerContributor().getInfo(myFixture.file))
    }
}
