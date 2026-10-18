package dev.robotcode.robotcode4ij.configuration

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeSettingsPagesTest {

    @Test
    fun loadLibraryTimeoutAcceptsAnEmptyFieldAndOneTo3600Seconds() {
        assertEquals(0, parseLoadLibraryTimeout(""))
        assertEquals(0, parseLoadLibraryTimeout("  "))
        assertEquals(1, parseLoadLibraryTimeout("1"))
        assertEquals(30, parseLoadLibraryTimeout(" 30 "))
        assertEquals(3600, parseLoadLibraryTimeout("3600"))

        for (text in listOf("0", "-5", "3601", "1.5", "ten")) {
            assertNull(text, parseLoadLibraryTimeout(text))
        }
    }

    @Test
    fun fileCheckIntervalAcceptsOneTo1440Minutes() {
        assertEquals(1, parseFileCheckInterval("1"))
        assertEquals(5, parseFileCheckInterval(" 5 "))
        assertEquals(1440, parseFileCheckInterval("1440"))

        for (text in listOf("0", "-5", "1441", "1.5", "five", "", "  ")) {
            assertNull(text, parseFileCheckInterval(text))
        }
    }

    @Test
    fun listEntriesAreTrimmedWithoutBlankOnes() {
        assertEquals(
            listOf("KeywordNotFound", "VariableNotFound"),
            parseListEntries(" KeywordNotFound; ;VariableNotFound ;;")
        )
        assertEquals(emptyList<String>(), parseListEntries(""))
        assertEquals(
            "KeywordNotFound; VariableNotFound",
            joinListEntries(listOf(" KeywordNotFound ", "", "VariableNotFound"))
        )
    }
}
