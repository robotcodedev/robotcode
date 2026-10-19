package dev.robotcode.robotcode4ij

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeWhatsNewTest {

    @Test
    fun newReleasesAreAnnounced() {
        assertTrue(shouldAnnounce(null, "2.8.0", true))
        assertTrue(shouldAnnounce("2.7.0", "2.8.0", true))
        assertTrue(shouldAnnounce("2.8.0-dev.508", "2.8.0", true))
    }

    @Test
    fun theSameVersionAndDevBuildsAreNotAnnounced() {
        assertFalse(shouldAnnounce("2.8.0", "2.8.0", true))
        assertFalse(shouldAnnounce("2.8.0-dev.483", "2.8.0-dev.508", true))
        assertFalse(shouldAnnounce("2.7.0", "2.8.0-dev.508", true))
        assertFalse(shouldAnnounce(null, "2.8.0-dev.508", true))
    }

    @Test
    fun aDowngradeIsAnnouncedAsInVsCode() {
        assertTrue(shouldAnnounce("2.8.0", "2.7.0", true))
    }

    @Test
    fun nothingIsAnnouncedWithTheSettingOff() {
        assertFalse(shouldAnnounce(null, "2.8.0", false))
        assertFalse(shouldAnnounce("2.7.0", "2.8.0", false))
    }

    @Test
    fun buildMetadataIsNoDevBuild() {
        assertTrue(isDevBuild("2.8.0-dev.508"))
        assertFalse(isDevBuild("2.8.0"))
        assertFalse(isDevBuild("2.8.0+build.5"))
        assertFalse(isDevBuild("2.8.0+build-5"))
    }
}
