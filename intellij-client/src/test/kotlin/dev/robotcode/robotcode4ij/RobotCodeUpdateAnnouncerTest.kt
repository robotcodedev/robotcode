package dev.robotcode.robotcode4ij

import com.intellij.ide.util.PropertiesComponent
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.configuration.RobotCodeApplicationConfiguration
import java.util.concurrent.Callable
import java.util.concurrent.CyclicBarrier
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class RobotCodeUpdateAnnouncerTest : BasePlatformTestCase() {

    private val properties get() = PropertiesComponent.getInstance()
    private val announcer get() = RobotCodeUpdateAnnouncer.getInstance()

    override fun setUp() {
        super.setUp()
        properties.unsetValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY)
    }

    override fun tearDown() {
        try {
            properties.unsetValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY)
            RobotCodeApplicationConfiguration.getInstance()
                .loadState(RobotCodeApplicationConfiguration.ApplicationState())
        } catch (e: Throwable) {
            addSuppressedException(e)
        } finally {
            super.tearDown()
        }
    }

    private val noted get() = properties.getValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY)

    fun testANewVersionIsAnnouncedOnce() {
        properties.setValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY, "2.7.0")

        assertTrue(announcer.noteVersion("2.8.0"))
        assertFalse(announcer.noteVersion("2.8.0"))
        assertEquals("2.8.0", noted)
    }

    fun testTheFirstStartAfterTheInstallationIsAnnounced() {
        assertTrue(announcer.noteVersion("2.8.0"))
    }

    fun testTheVersionIsNotedWithTheSettingOff() {
        RobotCodeApplicationConfiguration.getInstance().showWhatsNewOnUpdate = false

        assertFalse(announcer.noteVersion("2.8.0"))
        assertEquals("2.8.0", noted)
    }

    fun testADevBuildIsNotedButNotAnnounced() {
        properties.setValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY, "2.7.0")

        assertFalse(announcer.noteVersion("2.8.0-dev.508"))
        assertEquals("2.8.0-dev.508", noted)
    }

    fun testCallsAtTheSameTimeAnnounceOnce() {
        properties.setValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY, "2.7.0")
        val barrier = CyclicBarrier(2)
        val executor = Executors.newFixedThreadPool(2)
        try {
            val results = executor.invokeAll(List(2) {
                Callable {
                    barrier.await(10, TimeUnit.SECONDS)
                    announcer.noteVersion("2.8.0")
                }
            }).map { it.get(10, TimeUnit.SECONDS) }

            assertEquals(listOf(false, true), results.sorted())
        } finally {
            executor.shutdownNow()
        }
    }
}
