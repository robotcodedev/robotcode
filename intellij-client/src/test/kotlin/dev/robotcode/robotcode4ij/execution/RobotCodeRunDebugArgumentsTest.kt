package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.executors.DefaultDebugExecutor
import com.intellij.execution.executors.DefaultRunExecutor
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeRunDebugArgumentsTest {

    private fun resolved(values: RobotCodeRunConfigurationOptions.() -> Unit): RunDebugOptions {
        val configuration = RobotCodeRunConfigurationOptions().apply(values)
        return resolveRunDebugOptions(RobotCodeProjectConfiguration.ProjectState(), configuration)
    }

    private fun custom(command: String) =
        defaultRunDebugOptions.copy(wrapper = RobotRunWrapper.CUSTOM, wrapperCommand = command)

    // the decision takes only the executor, so a Debug run is in debug mode whichever runner runs it
    @Test
    fun onlyDebugRunsStartTheDebuggerInDebugMode() {
        val debug = isDebugExecutor(DefaultDebugExecutor.EXECUTOR_ID)
        val run = isDebugExecutor(DefaultRunExecutor.EXECUTOR_ID)

        assertTrue(debug)
        assertFalse(run)
        assertFalse("--no-debug" in debugArguments(debug, 5000, defaultRunDebugOptions, listOf()))
        assertTrue("--no-debug" in debugArguments(run, 5000, defaultRunDebugOptions, listOf()))
    }

    @Test
    fun eachWrapperState() {
        assertEquals(listOf<String>(), wrapperArguments(defaultRunDebugOptions))
        assertEquals(listOf("--wrapper", "xvfb-run -a"), wrapperArguments(custom("xvfb-run -a")))
        assertEquals(
            listOf("--no-wrapper"), wrapperArguments(defaultRunDebugOptions.copy(wrapper = RobotRunWrapper.NONE))
        )
    }

    // the command as Python's shlex.join writes it, which shlex.split turns back into the typed words
    @Test
    fun aWrapperReachesRobotcodeWithTheTypedWords() {
        val cases = listOf(
            "my-wrapper --title \"My Session\"" to "my-wrapper --title 'My Session'",
            "\"C:\\Program Files\\Wrap\\wrap.cmd\" -a" to "'C:\\Program Files\\Wrap\\wrap.cmd' -a",
            "say \"it's\"" to "say 'it'\"'\"'s'"
        )
        for ((typed, joined) in cases) {
            assertEquals(typed, listOf("--wrapper", joined), wrapperArguments(custom(typed)))
        }
    }

    @Test
    fun debuggerOptionsAreOnlyPassedWhenTheyDifferFromTheDebuggersDefaults() {
        // the options a Debug passes after the port for a configuration with the change
        fun assertPassed(expected: List<String>, change: RobotCodeRunConfigurationOptions.() -> Unit) {
            assertEquals(
                listOf("--tcp", "6612") + expected,
                debugArguments(debug = true, port = 6612, options = resolved(change), robotArguments = listOf())
            )
        }

        assertPassed(listOf()) {}
        assertPassed(listOf()) { outputMessages = RobotRunSwitch.OFF }
        assertPassed(listOf("--output-messages")) { outputMessages = RobotRunSwitch.ON }
        assertPassed(listOf()) { outputLog = RobotRunSwitch.ON }
        assertPassed(listOf("--no-output-log")) { outputLog = RobotRunSwitch.OFF }
        assertPassed(listOf()) { outputTimestamps = RobotRunSwitch.OFF }
        assertPassed(listOf("--output-timestamps")) { outputTimestamps = RobotRunSwitch.ON }
        assertPassed(listOf()) { connectionTimeout = 15 }
        assertPassed(listOf("--wait-for-client-timeout", "30")) { connectionTimeout = 30 }
        assertPassed(listOf("--stop-on-entry")) { stopOnEntry = true }
        assertPassed(listOf("--group-output", "--configuration-done-timeout", "20")) {
            debuggerArguments = "--group-output --configuration-done-timeout 20"
        }
    }

    @Test
    fun stopOnEntryOnlyUnderDebug() {
        val options = resolved { stopOnEntry = true }

        assertEquals(
            listOf("--tcp", "6612", "--stop-on-entry"),
            debugArguments(debug = true, port = 6612, options = options, robotArguments = listOf())
        )
        assertEquals(
            listOf("--no-debug", "--tcp", "6612"),
            debugArguments(debug = false, port = 6612, options = options, robotArguments = listOf())
        )
    }

    @Test
    fun theOptionsComeInTheOrderOfVSCodesLauncher() {
        val options = resolved {
            wrapper = RobotRunWrapper.CUSTOM
            wrapperCommand = "xvfb-run -a"
            robotCodeArguments = "--verbose"
            outputMessages = RobotRunSwitch.ON
            outputLog = RobotRunSwitch.OFF
            outputTimestamps = RobotRunSwitch.ON
            stopOnEntry = true
            connectionTimeout = 30
            debuggerArguments = "--group-output"
        }

        assertEquals(
            listOf(
                "--no-pager", "-dp", ".", "--wrapper", "xvfb-run -a", "--verbose", "debug", "--tcp", "6612",
                "--wait-for-client-timeout", "30", "--output-messages", "--no-output-log", "--output-timestamps",
                "--stop-on-entry", "--group-output", "--", "tests"
            ),
            runArguments(
                listOf(), paths = listOf(), debug = true, port = 6612, options = options,
                robotArguments = listOf("tests")
            )
        )
    }
}
