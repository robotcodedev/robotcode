package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.runConfigurationType
import com.intellij.openapi.util.JDOMUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.InterpreterKind
import dev.robotcode.robotcode4ij.PythonInterpreter
import org.jdom.Element

class RobotCodeRunConfigurationPersistenceTest : BasePlatformTestCase() {

    private val factory get() = runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()

    private fun newConfiguration() = RobotCodeRunConfiguration(project, factory)

    private fun roundTrip(configuration: RobotCodeRunConfiguration): RobotCodeRunConfiguration {
        val element = Element("configuration")
        configuration.writeExternal(element)
        return newConfiguration().apply { readExternal(element) }
    }

    private fun item(kind: String?, name: String) = RobotRunSelectionItem().apply {
        this.kind = kind
        this.name = name
        relSource = "tests/sample.robot"
        suite = "Project.Tests.Sample"
        suiteRelSource = "tests/sample.robot"
    }

    private fun assertSameTarget(expected: RobotCodeRunConfiguration, actual: RobotCodeRunConfiguration) {
        assertEquals(expected.options.targetKind, actual.options.targetKind)
        assertEquals(expected.options.targetPaths, actual.options.targetPaths)
        assertEquals(expected.options.topLevelSuite, actual.options.topLevelSuite)
        assertEquals(expected.options.selection, actual.options.selection)
    }

    fun testEachTargetSurvivesWritingAndCloning() {
        val targets = listOf<RobotCodeRunConfiguration.() -> Unit>(
            { options.targetKind = RobotRunTargetKind.PATHS },
            {
                options.targetKind = RobotRunTargetKind.PATHS
                options.targetPaths = mutableListOf("tests/other.robot", "C:\\Robot Tests\\a b.robot")
            },
            {
                options.targetKind = RobotRunTargetKind.SELECTION
                options.topLevelSuite = "Project"
                options.selection = mutableListOf(
                    item("test", "Project.Tests.Sample.First Test Passes"), item(null, "Project.Tests.Other")
                )
            },
        )
        for (target in targets) {
            val configuration = newConfiguration().apply(target)

            assertSameTarget(configuration, roundTrip(configuration))
            assertSameTarget(configuration, configuration.clone() as RobotCodeRunConfiguration)
        }
    }

    fun testPyCharmFieldsSurviveNextToTheTarget() {
        val configuration = newConfiguration().apply {
            options.targetKind = RobotRunTargetKind.PATHS
            options.targetPaths = mutableListOf("tests")
            interpreterOptions = "-O"
            envs = mapOf("FOO" to "bar")
            workingDirectory = "/work"
            isUseModuleSdk = false
            sdkHome = "/usr/bin/python3"
        }

        for (copy in listOf(roundTrip(configuration), configuration.clone() as RobotCodeRunConfiguration)) {
            assertEquals("-O", copy.interpreterOptions)
            assertEquals("bar", copy.envs["FOO"])
            assertEquals("/work", copy.workingDirectory)
            assertFalse(copy.isUseModuleSdk)
            assertEquals("/usr/bin/python3", copy.sdkHome)
            assertSameTarget(configuration, copy)
        }
    }

    fun testNewConfigurationRunsAsBefore() {
        val configuration = newConfiguration()

        assertEquals(RobotRunTargetKind.PATHS, configuration.options.targetKind)
        assertEquals(listOf<String>(), configuration.options.targetPaths)
        assertTrue(configuration.isUseModuleSdk)
        assertEquals("", configuration.workingDirectory)
        assertFalse(configuration.shouldAddContentRoots())
        assertFalse(configuration.shouldAddSourceRoots())
    }

    fun testConfigurationOfVersion27OpensWithTheDefaults() {
        // as version 2.7 wrote a temporary configuration that a gutter run created
        val element = JDOMUtil.load(
            """
            <configuration name="Test First Test Passes" type="RobotCodeConfigurationType"
                           factoryName="ROBOT_FRAMEWORK_TEST" temporary="true">
              <method v="2" />
            </configuration>
            """.trimIndent()
        )

        val configuration = newConfiguration().apply { readExternal(element) }

        // PyCharm's editor cannot show a configuration without interpreter options
        assertEquals("", configuration.interpreterOptions)
        assertEquals(RobotRunTargetKind.PATHS, configuration.options.targetKind)
        assertEquals(listOf<String>(), configuration.options.targetPaths)
        assertTrue(configuration.isUseModuleSdk)
        assertEquals("", configuration.workingDirectory)
        assertFalse(configuration.shouldAddContentRoots())
        assertFalse(configuration.shouldAddSourceRoots())
    }

    fun testPythonPathOptionsThatTheUserSwitchedOnStayOn() {
        val configuration = newConfiguration().apply {
            setAddContentRoots(true)
            setAddSourceRoots(true)
        }

        val copy = roundTrip(configuration)

        assertTrue(copy.shouldAddContentRoots())
        assertTrue(copy.shouldAddSourceRoots())
    }

    fun testRemoteInterpretersAreRefused() {
        assertNotNull(interpreterRefusal(PythonInterpreter(InterpreterKind.REMOTE, "WSL", "/usr/bin/python3")))
        assertNull(interpreterRefusal(PythonInterpreter(InterpreterKind.LOCAL, "venv", "/work/.venv/bin/python")))
    }
}
