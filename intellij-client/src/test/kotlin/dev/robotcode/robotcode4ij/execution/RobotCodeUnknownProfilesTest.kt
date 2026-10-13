package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.configuration.ProfileInfo
import dev.robotcode.robotcode4ij.configuration.ProfileList
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeUnknownProfilesTest {

    private val list = ProfileList(listOf(ProfileInfo("ci"), ProfileInfo("development")))

    private fun custom(vararg names: String) = RobotCodeRunConfigurationOptions().apply {
        profilesKind = RobotRunProfilesKind.CUSTOM
        profiles = names.toMutableList()
    }

    @Test
    fun aNameThatRobotTomlNoLongerDefines() {
        assertEquals(listOf("dev"), unknownProfiles(custom("ci", "dev"), list))
    }

    @Test
    fun allNamesKnown() {
        assertEquals(listOf<String>(), unknownProfiles(custom("ci", " development "), list))
    }

    // the check reads only the cache, which is empty until the list was read
    @Test
    fun anEmptyCacheReportsNothing() {
        assertEquals(listOf<String>(), unknownProfiles(custom("dev"), null))
    }

    @Test
    fun onlyCustomProfilesAreChecked() {
        val options = custom("dev").apply { profilesKind = RobotRunProfilesKind.PROJECT }

        assertEquals(listOf<String>(), unknownProfiles(options, list))
    }

    @Test
    fun aListWithoutProfiles() {
        val none = ProfileList(messages = listOf("No profiles defined."))

        assertEquals(listOf("dev"), unknownProfiles(custom("dev"), none))
        assertEquals(listOf<String>(), unknownProfiles(custom("dev"), ProfileList()))
    }
}
