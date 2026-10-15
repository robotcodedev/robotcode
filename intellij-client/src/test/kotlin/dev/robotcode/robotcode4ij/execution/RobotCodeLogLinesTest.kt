package dev.robotcode.robotcode4ij.execution

import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeLogLinesTest {

    private val source = "/home/me/my project/tests/sample.robot"

    @Test
    fun anInfoMessageHasNoLevelAndNoColor() {
        assertEquals("should not in console ($source:4)\n", logLine("should not in console\n", source, 4))
    }

    @Test
    fun theLevelsHaveTheColorsOfTheConsole() {
        assertEquals(
            "\u001b[33m[ WARN ] a warning ($source:5)\u001b[0m\n", logLine("[ WARN ] a warning\n", source, 5)
        )
        assertEquals("\u001b[31m[ ERROR ] an error\u001b[0m\n", logLine("[ ERROR ] an error\n", null, null))
        assertEquals("\u001b[31m[ FAIL ] 1 != 0\u001b[0m\n", logLine("[ FAIL ] 1 != 0\n", null, null))
        assertEquals("\u001b[90m[ DEBUG ] details\u001b[0m\n", logLine("[ DEBUG ] details\n", null, null))
        assertEquals("\u001b[90m[ TRACE ] Arguments: [ ]\u001b[0m\n", logLine("[ TRACE ] Arguments: [ ]\n", null, null))
    }

    @Test
    fun theTimeOfAMessageComesBeforeItsLevel() {
        assertEquals(
            "\u001b[33m10:00:00.123 [ WARN ] a warning\u001b[0m\n",
            logLine("10:00:00.123 [ WARN ] a warning\n", null, null)
        )
    }

    @Test
    fun aMessageOfSeveralLinesIsColoredOnEachLineAndLocatedAtItsEnd() {
        assertEquals(
            "\u001b[33m[ WARN ] first\u001b[0m\n\u001b[33msecond ($source:7)\u001b[0m\n",
            logLine("[ WARN ] first\nsecond\n", source, 7)
        )
    }

    @Test
    fun noLocationWithoutASourceOrALine() {
        assertEquals("hello\n", logLine("hello\n", null, 3))
        assertEquals("hello\n", logLine("hello\n", source, 0))
        assertEquals("hello\n", logLine("hello\n", source, null))
    }

    @Test
    fun aWindowsPathStaysAsTheDebuggerSendsIt() {
        val windows = "C:\\Users\\me\\project\\tests\\sample.robot"
        assertEquals("hello ($windows:2)\n", logLine("hello\n", windows, 2))
    }

    @Test
    fun aMessageThatTheDebuggerColoredKeepsItsColors() {
        val colored = "[ \u001b[38;5;3mWARN\u001b[0m ] a warning\n"
        assertEquals("[ \u001b[38;5;3mWARN\u001b[0m ] a warning ($source:5)\n", logLine(colored, source, 5))
    }

    @Test
    fun aMessageWithoutALineBreak() {
        assertEquals("before", logLine("before", null, null))
    }
}
