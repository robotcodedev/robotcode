package dev.robotcode.robotcode4ij.configuration

import com.intellij.execution.process.ProcessOutput
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeProfilesTest {

    // the output of `robotcode --format json profiles list` without -p for a robot.toml with default-profiles = ["dev"]
    private val defaultOutput = """{"profiles":[""" +
        """{"name":"ci","enabled":false,"description":"CI","selected":false,"precedence":null},""" +
        """{"name":"dev","enabled":true,"description":"Development","selected":true,"precedence":null}]}"""

    private fun read(stdout: String): ProfileList {
        return (profileListResult(ProcessOutput(stdout, "", 0, false, false)) as ProfileListResult.Read).list
    }

    private fun profile(name: String, selected: Boolean = false) = ProfileInfo(name, "", selected)

    @Test
    fun outputIsDecodedWithoutTheKeysThatAreNotUsed() {
        assertEquals(
            ProfileList(listOf(ProfileInfo("ci", "CI", false), ProfileInfo("dev", "Development", true))),
            read(defaultOutput)
        )
        assertEquals(
            ProfileList(messages = listOf("No profiles defined.")),
            read("""{"profiles":[],"messages":["No profiles defined."]}""")
        )
    }

    @Test
    fun profilesThatRobotcodeReportsAsSelectedAreChecked() {
        // without a selection, those of default-profiles
        assertEquals(listOf("dev"), profileChoice(emptyList(), read(defaultOutput)).checked)

        // with one, also the profiles that a selected profile inherits
        val list = ProfileList(listOf(profile("base", selected = true), profile("ci", selected = true), profile("dev")))
        assertEquals(listOf("base", "ci"), profileChoice(listOf("ci"), list).checked)
    }

    @Test
    fun selectedNamesThatAreNotListedAreRemoved() {
        val list = ProfileList(listOf(profile("ci"), profile("dev", selected = true)))

        val choice = profileChoice(listOf("gone", "dev"), list)

        assertEquals(listOf("gone"), choice.removed)
        assertEquals(listOf("dev"), choice.selection)
    }

    @Test
    fun aListThatCouldNotBeReadRemovesNothing() {
        val unknown = profileChoice(listOf("dev"), ProfileList())
        assertEquals(emptyList<String>(), unknown.removed)
        assertEquals(listOf("dev"), unknown.selection)

        // messages say why the list is empty, so the names are gone
        val noProfiles = profileChoice(listOf("dev"), ProfileList(messages = listOf("No profiles defined.")))
        assertEquals(listOf("dev"), noProfiles.removed)
        assertEquals(emptyList<String>(), noProfiles.selection)
        assertEquals(listOf("No profiles defined."), noProfiles.messages)
    }

    @Test
    fun confirmingStoresTheCheckedNames() {
        val choice = profileChoice(emptyList(), read(defaultOutput))

        // the unchanged checks of default-profiles become the selection, as in VS Code
        assertEquals(listOf("dev"), choice.confirm(choice.checked))
        assertEquals(listOf("ci", "dev"), choice.confirm(listOf("dev", "ci")))
        assertEquals(emptyList<String>(), choice.confirm(emptyList()))
    }

    @Test
    fun errorTextHasTheBeginningOfTheErrorOutput() {
        val stderr = (1..8).joinToString("\n") { "line $it" }
        val error = profileListResult(ProcessOutput("", "\n$stderr\n", 255, false, false)) as ProfileListResult.Error

        assertTrue(error.message, error.message.startsWith("robotcode could not read the configuration profiles: "))
        assertTrue(error.message, error.message.endsWith("line 1\nline 2\nline 3\nline 4\nline 5"))

        assertEquals(
            ProfileListResult.Error("robotcode could not read the configuration profiles: it ended with exit code 1."),
            profileListResult(ProcessOutput("", "", 1, false, false))
        )
        assertEquals(
            ProfileListResult.Error(
                "robotcode could not read the configuration profiles: its output was not the expected one."
            ),
            profileListResult(ProcessOutput("profiles: []", "", 0, false, false))
        )
    }
}
