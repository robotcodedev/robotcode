package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.CantRunException
import com.intellij.execution.configurations.RuntimeConfigurationError
import com.intellij.execution.configurations.RuntimeConfigurationException
import com.intellij.execution.configurations.RuntimeConfigurationWarning
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.runners.ExecutionEnvironmentBuilder
import com.intellij.openapi.application.WriteAction
import com.intellij.openapi.projectRoots.ProjectJdkTable
import com.intellij.openapi.projectRoots.Sdk
import com.intellij.openapi.projectRoots.SdkAdditionalData
import com.intellij.openapi.util.io.FileUtil
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.jetbrains.python.sdk.PyRemoteSdkAdditionalDataMarker
import com.jetbrains.python.sdk.PythonSdkType
import dev.robotcode.robotcode4ij.EnvironmentResult
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.PythonInterpreter
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.pythonInterpreterOf
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.testManger
import org.junit.Assert
import java.lang.reflect.Proxy
import java.nio.file.Path

/**
 * What a Robot Framework run configuration reports before it runs: about its interpreter, from results of the check
 * that exist, and about its target.
 */
class RobotCodeRunConfigurationCheckTest : BasePlatformTestCase() {

    private val environment get() = project.robotCodeEnvironment
    private val factory get() = runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
    private val usable = EnvironmentState.Checked(EnvironmentResult.Usable)
    private val notInstalled = EnvironmentState.Checked(EnvironmentResult.RobotNotInstalled)

    override fun setUp() {
        super.setUp()
        environment.resetForTests()
    }

    override fun tearDown() {
        try {
            // a check that a test requested would otherwise end during the next test
            PlatformTestUtil.waitWithEventsDispatching(
                "the requested check did not end",
                { interpreters.none { environment.state(it) == EnvironmentState.Checking } },
                30
            )
            environment.resetForTests()
            project.testManger.setTestItemsForTests(arrayOf())
        } finally {
            super.tearDown()
        }
    }

    private val interpreters = mutableListOf<PythonInterpreter>()

    // a configuration with an interpreter of its own at [path], which no module of the project has
    private fun configurationWith(path: String): Pair<RobotCodeRunConfiguration, PythonInterpreter> {
        val sdk = ProjectJdkTable.getInstance().createSdk("Python of the configuration", PythonSdkType.getInstance())
        val modificator = sdk.sdkModificator
        modificator.homePath = path
        WriteAction.run<Throwable> {
            modificator.commitChanges()
            ProjectJdkTable.getInstance().addJdk(sdk, testRootDisposable)
        }
        return configurationWith(sdk)
    }

    private fun configurationWith(sdk: Sdk): Pair<RobotCodeRunConfiguration, PythonInterpreter> {
        val configuration = RobotCodeRunConfiguration(project, factory).apply {
            isUseModuleSdk = false
            this.sdk = sdk
        }
        return configuration to pythonInterpreterOf(sdk).also { interpreters += it }
    }

    // a path that does not exist, as an SDK stores it, so that a check of it starts no process
    private fun missingPython(): String {
        return FileUtil.toSystemIndependentName(
            Path.of(FileUtil.getTempDirectory(), "robotcode-no-python-check", "python").toString()
        )
    }

    private fun java(): String {
        return ProcessHandle.current().info().command()
            .orElse(Path.of(System.getProperty("java.home"), "bin", "java").toString())
    }

    private fun problem(configuration: RobotCodeRunConfiguration): RuntimeConfigurationException? {
        return try {
            configuration.checkConfiguration()
            null
        } catch (e: RuntimeConfigurationException) {
            e
        }
    }

    fun testUsableInterpreterReportsNothing() {
        val (configuration, interpreter) = configurationWith(missingPython())
        environment.checks.setState(interpreter, usable)

        assertNull(problem(configuration))
    }

    fun testUnusableResultIsAnErrorWithAFix() {
        val (configuration, interpreter) = configurationWith(missingPython())
        for (result in listOf(
            EnvironmentResult.RobotNotInstalled, EnvironmentResult.RobotTooOld("4.1"),
            EnvironmentResult.PythonTooOld("3.9"), EnvironmentResult.PathNotFound(missingPython())
        )) {
            environment.checks.setState(interpreter, EnvironmentState.Checked(result))

            val problem = problem(configuration)

            assertInstanceOf(problem, RuntimeConfigurationError::class.java)
            assertEquals(result.message, problem!!.localizedMessage)
            assertNotNull(problem.configurationQuickFix)
        }
    }

    // A registered SDK keeps only additional data that its type can store, so the remote SDK is a stand-in.
    fun testRemoteInterpreterIsAnErrorWithoutAFix() {
        val remoteData = object : SdkAdditionalData, PyRemoteSdkAdditionalDataMarker {}
        val sdk = Proxy.newProxyInstance(javaClass.classLoader, arrayOf(Sdk::class.java)) { proxy, method, args ->
            when (method.name) {
                "getName", "toString" -> "Remote Python"
                "getHomePath" -> "/usr/bin/python3"
                "getSdkAdditionalData" -> remoteData
                "getSdkType" -> PythonSdkType.getInstance()
                "hashCode" -> System.identityHashCode(proxy)
                "equals" -> proxy === args?.get(0)
                else -> null
            }
        } as Sdk
        val (configuration, _) = configurationWith(sdk)

        val problem = problem(configuration)

        assertInstanceOf(problem, RuntimeConfigurationError::class.java)
        assertEquals(RobotCodeBundle.message("run.remoteInterpreter"), problem!!.localizedMessage)
        assertNull(problem.configurationQuickFix)
    }

    fun testFailedCheckIsAWarning() {
        val (configuration, interpreter) = configurationWith(missingPython())
        val failed = EnvironmentState.Failed(RobotCodeBundle.message("python.check.timeout"))
        environment.checks.setState(interpreter, failed)

        val problem = problem(configuration)

        assertInstanceOf(problem, RuntimeConfigurationWarning::class.java)
        assertEquals(failed.message, problem!!.localizedMessage)
    }

    fun testInterpreterWithoutAResultIsCheckedInTheBackgroundAndReportsNothing() {
        val (configuration, interpreter) = configurationWith(missingPython())

        assertNull(problem(configuration))

        PlatformTestUtil.waitWithEventsDispatching(
            "no check was requested", { environment.state(interpreter) is EnvironmentState.Checked }, 10
        )
        assertEquals(
            EnvironmentState.Checked(EnvironmentResult.PathNotFound(missingPython())), environment.state(interpreter)
        )
    }

    // the check of an interpreter that exists runs a process, which the validation does not wait for
    fun testValidationStartsNoProcess() {
        val (configuration, interpreter) = configurationWith(java())

        assertNull(problem(configuration))

        assertEquals(EnvironmentState.Checking, environment.state(interpreter))
    }

    fun testConfigurationWithoutAnInterpreterGetsOnlyPyCharmsError() {
        // the module of the light test has no interpreter
        val configuration = RobotCodeRunConfiguration(project, factory)
        val ours = listOf(EnvironmentResult.NoInterpreter.message, RobotCodeBundle.message("run.remoteInterpreter"))

        val problem = problem(configuration)

        assertInstanceOf(problem, RuntimeConfigurationError::class.java)
        assertFalse(problem!!.localizedMessage, problem.localizedMessage in ours)
        assertEquals(EnvironmentState.Unknown, environment.state(pythonInterpreterOf(null)))
    }

    private fun stateOf(configuration: RobotCodeRunConfiguration) = configuration.getState(
        DefaultRunExecutor.getRunExecutorInstance(),
        ExecutionEnvironmentBuilder.create(project, DefaultRunExecutor.getRunExecutorInstance(), configuration).build()
    )

    fun testRunFollowsTheInterpreterOfTheConfigurationNotTheProjects() {
        val (configuration, interpreter) = configurationWith(missingPython())
        environment.checks.setState(interpreter, usable)
        environment.checks.setState(environment.projectInterpreter, notInstalled)

        assertInstanceOf(stateOf(configuration), RobotCodeRunProfileState::class.java)

        environment.checks.setState(interpreter, notInstalled)
        environment.checks.setState(environment.projectInterpreter, usable)

        val error = Assert.assertThrows(CantRunException::class.java) { stateOf(configuration) }
        assertEquals(notInstalled.message, error.message)
    }

    // the target, with a usable interpreter

    private fun configurationWithTarget(block: RobotCodeRunConfigurationOptions.() -> Unit): RobotCodeRunConfiguration {
        val (configuration, interpreter) = configurationWith(missingPython())
        environment.checks.setState(interpreter, usable)
        configuration.options.apply(block)
        return configuration
    }

    fun testMissingPathOfTheTargetIsAnError() {
        val configuration = configurationWithTarget {
            targetKind = RobotRunTargetKind.PATHS
            targetPaths = mutableListOf("tests/gone.robot")
        }

        val problem = problem(configuration)

        assertInstanceOf(problem, RuntimeConfigurationError::class.java)
        assertEquals(
            RobotCodeBundle.message("run.target.paths.missing", "\"tests/gone.robot\"", 1), problem!!.localizedMessage
        )
    }

    fun testExistingPathOfTheTargetReportsNothing() {
        val folder = FileUtil.createTempDirectory("robotcode-target", null)
        val configuration = configurationWithTarget {
            targetKind = RobotRunTargetKind.PATHS
            targetPaths = mutableListOf(FileUtil.toSystemIndependentName(folder.path))
        }

        assertNull(problem(configuration))
    }

    private val model = arrayOf(
        RobotCodeTestItem(
            type = "workspace", id = "workspace", name = "Project", longname = "Project",
            children = arrayOf(
                RobotCodeTestItem(
                    type = "suite", id = "suite", name = "Sample", longname = "Project.Sample",
                    children = arrayOf(
                        RobotCodeTestItem(type = "test", id = "test", name = "First", longname = "Project.Sample.First")
                    )
                )
            )
        )
    )

    private fun selection(vararg names: String) = configurationWithTarget {
        targetKind = RobotRunTargetKind.SELECTION
        selection = names.map { item ->
            RobotRunSelectionItem().apply {
                kind = "test"
                name = item
            }
        }.toMutableList()
    }

    fun testItemThatTheDiscoveryDidNotFindIsAWarning() {
        project.testManger.setTestItemsForTests(model)
        val configuration = selection("Project.Sample.First", "Project.Sample.Renamed")

        val problem = problem(configuration)

        assertInstanceOf(problem, RuntimeConfigurationWarning::class.java)
        assertEquals(
            RobotCodeBundle.message("run.target.selection.stale", "\"Project.Sample.Renamed\"", 1),
            problem!!.localizedMessage
        )
    }

    fun testItemThatTheDiscoveryFoundReportsNothing() {
        project.testManger.setTestItemsForTests(model)

        assertNull(problem(selection("Project.Sample.First")))
    }

    fun testItemsWithoutADiscoveryResultReportNothing() {
        assertNull(problem(selection("Project.Sample.Renamed")))
    }

    // discovery runs with the profiles of the project, which the configuration takes by default
    fun testItemsOfAConfigurationWithOtherProfilesReportNothing() {
        project.testManger.setTestItemsForTests(model)
        val configuration = selection("Project.Sample.Renamed")
        assertInstanceOf(problem(configuration), RuntimeConfigurationWarning::class.java)

        configuration.options.profilesKind = RobotRunProfilesKind.CUSTOM
        configuration.options.profiles = mutableListOf("other")

        assertNull(problem(configuration))
    }
}
