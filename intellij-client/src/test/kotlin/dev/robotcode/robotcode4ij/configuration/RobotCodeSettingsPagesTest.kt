package dev.robotcode.robotcode4ij.configuration

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class RobotCodeSettingsPagesTest {

    @get:Rule
    val temporaryFolder = TemporaryFolder()

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

    @Test
    fun relativeRobocopConfigurationFileIsResolvedAgainstTheProjectFolder() {
        val projectDir = temporaryFolder.root.toPath()
        val configFile = projectDir.resolve("robocop.toml")

        assertEquals(configFile, resolveRobocopConfigFile("robocop.toml", projectDir))
        assertEquals(configFile, resolveRobocopConfigFile(" ./sub/../robocop.toml ", projectDir))
        assertEquals(configFile, resolveRobocopConfigFile(configFile.toString(), projectDir))
        assertTrue(resolveRobocopConfigFile("robocop.toml", projectDir)!!.isAbsolute)
        assertNull(resolveRobocopConfigFile("\u0000", projectDir))
    }

    @Test
    fun robocopConfigurationFileMustExist() {
        val projectDir = temporaryFolder.root.toPath()
        temporaryFolder.newFile("robocop.toml")

        assertTrue(isExistingRobocopConfigFile("", projectDir))
        assertTrue(isExistingRobocopConfigFile("robocop.toml", projectDir))
        assertTrue(isExistingRobocopConfigFile(projectDir.resolve("robocop.toml").toString(), projectDir))
        assertFalse(isExistingRobocopConfigFile("missing.toml", projectDir))
        assertFalse(isExistingRobocopConfigFile(".", projectDir))
        assertFalse(isExistingRobocopConfigFile("\u0000", projectDir))
    }
}
