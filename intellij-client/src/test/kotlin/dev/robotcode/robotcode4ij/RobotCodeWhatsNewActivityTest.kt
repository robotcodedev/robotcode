package dev.robotcode.robotcode4ij

import com.intellij.ide.util.PropertiesComponent
import com.intellij.notification.Notification
import com.intellij.notification.Notifications
import com.intellij.testFramework.HeavyPlatformTestCase
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.common.timeoutRunBlocking

/**
 * The startup activity, in a project of its own because it registers listeners: a project that a Robot Framework file
 * marked before the version was known gets the announcement when the activity runs.
 */
class RobotCodeWhatsNewActivityTest : HeavyPlatformTestCase() {

    private val properties get() = PropertiesComponent.getInstance()
    private val announcer get() = RobotCodeUpdateAnnouncer.getInstance()
    private var pluginVersion: String? = null

    override fun setUp() {
        super.setUp()
        assertNotNull(platformStartupActivity())
        pluginVersion = announcer.pluginVersion
        properties.setValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY, "2.7.0")
    }

    override fun tearDown() {
        try {
            properties.unsetValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY)
            announcer.pluginVersion = pluginVersion
        } catch (e: Throwable) {
            addSuppressedException(e)
        } finally {
            super.tearDown()
        }
    }

    fun testAProjectMarkedBeforeTheVersionWasKnownIsAnnouncedWhenTheActivityRuns() {
        val notifications = mutableListOf<Notification>()
        project.messageBus.connect(testRootDisposable).subscribe(Notifications.TOPIC, object : Notifications {
            override fun notify(notification: Notification) {
                if (notification.content.startsWith("RobotCode has been updated")) {
                    notifications += notification
                }
            }
        })

        announcer.pluginVersion = null
        project.robotCodeEnvironment.markRobotProject()
        PlatformTestUtil.dispatchAllEventsInIdeEventQueue()
        assertEmpty(notifications)

        announcer.pluginVersion = "2.8.0"
        timeoutRunBlocking { RobotCodePostStartupActivity().execute(project) }
        PlatformTestUtil.dispatchAllEventsInIdeEventQueue()

        assertEquals(1, notifications.size)
        assertTrue(notifications.single().content.contains("v2.8.0."))
    }
}
