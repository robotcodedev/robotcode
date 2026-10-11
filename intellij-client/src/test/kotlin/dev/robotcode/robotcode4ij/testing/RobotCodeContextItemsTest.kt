package dev.robotcode.robotcode4ij.testing

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeContextItemsTest {

    // tests start on lines 4 and 8, followed by a keyword section
    private val suite = """
        *** Settings ***
        Library    Collections

        *** Test Cases ***
        First Test Passes
            Log    first
            Build Greeting

        Second Test
            Log    second

        *** Keywords ***
        Build Greeting
            Log    greeting
    """.trimIndent().lines()

    private fun enclosing(lines: List<String>, startLines: List<Int>, caretLine: Int) =
        enclosingTestLine(startLines, caretLine) { lines[it] }

    @Test
    fun caretMapsToTheTestWhoseBodyHoldsIt() {
        val tests = listOf(4, 8)
        val cases = listOf(
            "on the name line of a test" to (4 to 4),
            "in the body of a test" to (6 to 4),
            "on an empty line between two tests" to (7 to 4),
            "in the body of the second test" to (9 to 8),
            "on line 1" to (0 to null),
            "on a section header row" to (11 to null),
            "in the body of a keyword after the tests" to (13 to null),
        )
        for ((case, value) in cases) {
            val (caret, expected) = value
            assertEquals(case, expected, enclosing(suite, tests, caret))
        }
    }

    @Test
    fun translatedHeadersAndThePipeFormatAreSectionHeaders() {
        val german = "Language: de\n\n*** Testfälle ***\nErster Test\n    Log    x\n".lines()
        assertEquals(3, enclosing(german, listOf(3), 4))

        assertTrue(isSectionHeaderRow("*** Schlüsselwörter ***"))
        assertTrue(isSectionHeaderRow("| *** Keywords *** |"))
        assertFalse(isSectionHeaderRow("|    | Log | x |"))
        assertFalse(isSectionHeaderRow("    *** not a header ***"))
        assertFalse(isSectionHeaderRow("First Test Passes"))
    }
}
