package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.configurations.RunConfiguration
import com.intellij.execution.configurations.RunProfile
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.runners.ExecutionEnvironmentBuilder
import com.intellij.icons.AllIcons
import com.intellij.openapi.wm.ToolWindowId
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import javax.swing.Icon

// an executor with the id of one of PyCharm Professional's, which the IDE of the tests need not have
private class ExecutorWithId(private val id: String) : Executor() {
    override fun getToolWindowId(): String = ToolWindowId.RUN
    override fun getToolWindowIcon(): Icon = AllIcons.Actions.Execute
    override fun getIcon(): Icon = AllIcons.Actions.Execute
    override fun getDisabledIcon(): Icon? = null
    override fun getDescription(): String = id
    override fun getActionName(): String = id
    override fun getId(): String = id
    override fun getStartActionText(): String = id
    override fun getContextActionId(): String = "$id.context"
    override fun getHelpId(): String? = null
}

class RobotCodeProfileRunnerTest : BasePlatformTestCase() {

    private val runner = RobotCodeProfileRunner()

    private fun robotConfiguration(): RunConfiguration =
        runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
            .createTemplateConfiguration(project)

    fun testTakesProfileAndConcurrencyDiagramOfARobotFrameworkConfiguration() {
        val configuration = robotConfiguration()

        assertTrue(runner.canRun("Profiler", configuration))
        assertTrue(runner.canRun("ConcurrencyExecutor", configuration))
    }

    fun testTakesNoOtherExecutorAndNoOtherConfiguration() {
        val configuration = robotConfiguration()
        val other = object : RunProfile {
            override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState? = null
            override fun getName(): String = "Python"
            override fun getIcon(): Icon? = null
        }

        assertFalse(runner.canRun(DefaultRunExecutor.EXECUTOR_ID, configuration))
        assertFalse(runner.canRun(DefaultDebugExecutor.EXECUTOR_ID, configuration))
        assertFalse(runner.canRun("Profiler", other))
        assertFalse(runner.canRun("ConcurrencyExecutor", other))
    }

    fun testEndsEachRunWithTheMessageOfItsExecutor() {
        val messages = mapOf(
            "Profiler" to "Robot Framework runs cannot be profiled.",
            "ConcurrencyExecutor" to "Robot Framework runs have no concurrency diagram.",
        )
        for ((executorId, message) in messages) {
            val environment =
                ExecutionEnvironmentBuilder.create(project, ExecutorWithId(executorId), robotConfiguration()).build()
            var error: Throwable? = null

            unsupportedRun(environment).onError { error = it }

            assertEquals(message, error?.message)
        }
    }
}
