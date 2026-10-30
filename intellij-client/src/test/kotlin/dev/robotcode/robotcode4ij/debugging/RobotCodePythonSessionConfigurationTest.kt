package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.BeforeRunTask
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.openapi.util.Key
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.jetbrains.python.parser.icons.PythonParserIcons
import dev.robotcode.robotcode4ij.execution.RobotCodeConfigurationType
import dev.robotcode.robotcode4ij.execution.RobotCodeRunConfiguration
import dev.robotcode.robotcode4ij.execution.RobotRunSwitch

private val SOME_TASK: Key<SomeTask> = Key.create("RobotCodeTestBeforeRunTask")

private class SomeTask : BeforeRunTask<SomeTask>(SOME_TASK)

class RobotCodePythonSessionConfigurationTest : BasePlatformTestCase() {

    private val factory get() = runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()

    fun testThePythonSessionRunsACopyWithItsNameAndIconWithoutBeforeLaunchTasks() {
        val configuration = RobotCodeRunConfiguration(project, factory).apply {
            name = "Orders"
            workingDirectory = "/work/orders"
            options.attachPython = RobotRunSwitch.ON
            options.targetPaths = mutableListOf("tests/orders.robot")
            beforeRunTasks = listOf(SomeTask())
        }

        val copy = pythonSessionConfiguration(configuration)

        assertNotSame(configuration, copy)
        assertEquals("Python Orders", copy.name)
        assertSame(PythonParserIcons.PythonFile, copy.icon)
        assertEmpty(copy.beforeRunTasks)
        assertEquals("/work/orders", copy.workingDirectory)
        assertEquals(RobotRunSwitch.ON, copy.options.attachPython)
        assertEquals(listOf("tests/orders.robot"), copy.options.targetPaths)
        assertEquals("Orders", configuration.name)
        assertSame(factory.icon, configuration.icon)
        assertEquals(1, configuration.beforeRunTasks.size)
    }
}
