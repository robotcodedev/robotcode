package dev.robotcode.robotcode4ij

import com.intellij.execution.process.ProcessOutput
import dev.robotcode.robotcode4ij.CheckPythonAndRobotVersionResult.INVALID_PYTHON_VERSION
import dev.robotcode.robotcode4ij.CheckPythonAndRobotVersionResult.OK
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private const val REQUIREMENT = "Python 3.10 or newer with Robot Framework 5.0 or newer"

class CheckPythonAndRobotVersionTest {

    @Test
    fun probeThatPrintsTrueAcceptsThePython() {
        assertEquals(OK, pythonVersionResult(ProcessOutput("True\n", "", 0, false, false)))
    }

    @Test
    fun probeThatPrintsFalseOrFailsMeansAPythonOlderThan310() {
        val outputs = listOf(ProcessOutput("False\n", "", 0, false, false), ProcessOutput("", "error", 1, false, false))
        for (output in outputs) {
            assertEquals(INVALID_PYTHON_VERSION, pythonVersionResult(output))
        }
    }

    @Test
    fun everyInterpreterTextNamesTheRequirement() {
        for (result in CheckPythonAndRobotVersionResult.entries.filter { it != OK }) {
            assertTrue(result.name, result.errorMessage!!.contains(REQUIREMENT))
        }
        assertNull(OK.errorMessage)
    }
}
