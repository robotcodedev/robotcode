package dev.robotcode.robotcode4ij

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.CapturingProcessHandler
import com.intellij.execution.process.ProcessOutput
import dev.robotcode.robotcode4ij.EnvironmentResult.PythonTooOld
import dev.robotcode.robotcode4ij.EnvironmentResult.RobotNotInstalled
import dev.robotcode.robotcode4ij.EnvironmentResult.RobotTooOld
import dev.robotcode.robotcode4ij.EnvironmentResult.Usable
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test

private const val REQUIREMENT = "Python 3.10 or newer with Robot Framework 5.0 or newer"

class RobotCodeEnvironmentProbeTest {

    private fun output(stdout: String, exitCode: Int = 0, timeout: Boolean = false) =
        ProcessOutput(stdout, "", exitCode, timeout, false)

    private fun probe(python: String, robot: String? = null): EnvironmentState {
        val robotPart = if (robot != null) ", \"robot\": \"$robot\"" else ", \"robotError\": \"ImportError: no robot\""
        return probeState(output("{\"python\": \"$python\"$robotPart}\n"))
    }

    @Test
    fun versionsGiveTheirResults() {
        assertEquals(EnvironmentState.Checked(PythonTooOld("3.9")), probe("3.9.18", "7.0"))
        assertEquals(EnvironmentState.Checked(RobotNotInstalled), probe("3.12.1"))
        assertEquals(EnvironmentState.Checked(RobotTooOld("4.1")), probe("3.12.1", "4.1"))
        for (robot in listOf("5.0", "6.1rc1", "7.0.1", "7.5")) {
            assertEquals(robot, EnvironmentState.Checked(Usable), probe("3.10.0", robot))
        }
    }

    @Test
    fun unexpectedOutputOrExitCodeIsAFailedCheck() {
        val outputs = listOf(
            output("Traceback (most recent call last):\n"),
            output("{\"robot\": \"7.0\"}\n"),
            output("", exitCode = 1),
            output("{\"python\": \"3.12.1\", \"robot\": \"7.0\"}\n", exitCode = 2),
            output("", exitCode = -1, timeout = true),
        )
        for (output in outputs) {
            assertTrue(output.toString(), probeState(output) is EnvironmentState.Failed)
        }
    }

    @Test
    fun versionNumbersStopAtTheFirstPartWithoutLeadingDigits() {
        assertEquals(listOf(3, 9, 18), versionNumbers("3.9.18"))
        assertEquals(listOf(6, 1), versionNumbers("6.1rc1"))
        assertEquals(listOf(7), versionNumbers("7.dev1"))
    }

    @Test
    fun everyResultTextNamesTheRequirement() {
        val results = listOf(
            EnvironmentResult.NoInterpreter,
            EnvironmentResult.PathNotFound("/usr/bin/python3"),
            PythonTooOld("3.9"),
            RobotNotInstalled,
            RobotTooOld("4.1"),
            EnvironmentResult.Remote,
        )
        for (result in results) {
            assertTrue(result.toString(), EnvironmentState.Checked(result).message.contains(REQUIREMENT))
        }
        assertTrue(EnvironmentState.Failed("it did not answer within 30 seconds.").message.contains(REQUIREMENT))
        assertTrue(PythonTooOld("3.9").message.contains("Python 3.9"))
        assertTrue(RobotTooOld("4.1").message.contains("Robot Framework 4.1"))
        assertEquals(null, Usable.message)
    }

    // Set ROBOTCODE_TEST_PYTHON to a Python with Robot Framework, such as the one of the `test.rf75` hatch environment.
    @Test
    fun snippetPrintsALineThatTheParserAccepts() {
        val python = System.getenv("ROBOTCODE_TEST_PYTHON")
        assumeTrue("ROBOTCODE_TEST_PYTHON is not set", !python.isNullOrEmpty())

        val output = CapturingProcessHandler(GeneralCommandLine(python, "-u", "-X", "utf8", "-c", PROBE_SNIPPET))
            .runProcess(30_000, true)

        assertEquals(output.stderr, EnvironmentState.Checked(Usable), probeState(output))
    }
}
