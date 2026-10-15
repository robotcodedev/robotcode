package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.configurations.RunConfiguration
import com.intellij.execution.configurations.RunConfigurationBase
import com.intellij.execution.configurations.RunProfileState
import com.intellij.execution.configurations.WrappingRunConfiguration
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.testframework.AbstractTestProxy
import com.intellij.execution.testframework.Filter
import com.intellij.execution.testframework.actions.AbstractRerunFailedTestsAction
import com.intellij.execution.testframework.sm.runner.SMTestProxy
import com.intellij.openapi.util.Disposer
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.util.Urls
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProgramRunner
import dev.robotcode.robotcode4ij.testing.decodeDiscoverResult

class RobotCodeRerunFailedTestsTest : BasePlatformTestCase() {

    private val factory get() = runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()

    // the output of `robotcode -dp . discover all` with Robot Framework 7.5
    private val model = javaClass.getResourceAsStream("/discover/selection-project.json")!!.bufferedReader()
        .use { decodeDiscoverResult(it.readText()).items!! }

    // a node as the converter starts it, with the location URL and the long name of the run
    private fun node(name: String, isSuite: Boolean, source: String, line: Int, longname: String) = SMTestProxy(
        name, isSuite,
        Urls.newUrl("robotcode", "/", Urls.newLocalFileUrl(source).toString())
            .addParameters(mapOf("line" to (line - 1).toString())).toString(),
        longname, false
    )

    // the platform's rerun wraps the configuration as its peer, as this wrapper does
    private fun wrapper(configuration: RunConfiguration) =
        object : RunConfigurationBase<Any>(project, factory, "Rerun"), WrappingRunConfiguration<RunConfiguration> {
            override fun getPeer() = configuration

            override fun getConfigurationEditor() = throw UnsupportedOperationException()

            override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState? = null
        }

    fun testTheCopyRunsOnlyTheFailedTest() {
        val configuration = RobotCodeRunConfiguration(project, factory)
        val properties = RobotRunnerConsoleProperties(
            configuration, "RobotCode", DefaultRunExecutor.getRunExecutorInstance()
        )
        Disposer.register(testRootDisposable, properties)
        // a run of the folder `tests`, whose top-level suite is named after the folder
        val source = "/project/tests/sample.robot"
        val root = SMTestProxy.SMRootTestProxy()
        val suite = node("Sample", true, source, 1, "Tests.Sample").also { root.addChild(it) }
        node("First Test Passes", false, source, 3, "Tests.Sample.First Test Passes").also {
            suite.addChild(it)
            it.setStarted()
            it.setFinished()
        }
        node("Second Test", false, source, 7, "Tests.Sample.Second Test").also {
            suite.addChild(it)
            it.setStarted()
            it.setTestFailed("intentional failure", null, false)
        }
        node("Skipped Test", false, source, 11, "Tests.Sample.Skipped Test").also {
            suite.addChild(it)
            it.setStarted()
            it.setTestIgnored("skipped", null)
        }
        suite.setTestFailed("", null, false)

        // the tests that the platform's action takes, as it takes them
        @Suppress("UNCHECKED_CAST")
        val filter = AbstractRerunFailedTestsAction.getFailuresFilter(properties) as Filter<AbstractTestProxy>
        val copy = rerunConfiguration(configuration, failedTestsOf(filter.select(root.allTests)), model)

        assertEquals(RobotRunTargetKind.SELECTION, copy.options.targetKind)
        assertEquals("Project", copy.options.topLevelSuite)
        assertEquals(listOf("Project.Tests.Sample.Second Test"), copy.options.selection.map { it.name })
        assertEquals(RobotRunTargetKind.PATHS, configuration.options.targetKind)
        assertTrue(configuration.options.selection.isEmpty())
    }

    fun testTheRunnersTakeTheRerunOfARobotFrameworkConfiguration() {
        val rerun = wrapper(RobotCodeRunConfiguration(project, factory))
        val other = wrapper(object : RunConfigurationBase<Any>(project, factory, "Other") {
            override fun getConfigurationEditor() = throw UnsupportedOperationException()

            override fun getState(executor: Executor, environment: ExecutionEnvironment): RunProfileState? = null
        })

        assertTrue(RobotCodeProgramRunner().canRun(DefaultRunExecutor.EXECUTOR_ID, rerun))
        assertTrue(RobotCodeDebugProgramRunner().canRun(DefaultDebugExecutor.EXECUTOR_ID, rerun))
        assertFalse(RobotCodeProgramRunner().canRun(DefaultDebugExecutor.EXECUTOR_ID, rerun))
        assertFalse(RobotCodeProgramRunner().canRun(DefaultRunExecutor.EXECUTOR_ID, other))
        assertFalse(RobotCodeDebugProgramRunner().canRun(DefaultDebugExecutor.EXECUTOR_ID, other))
    }
}
