package dev.robotcode.robotcode4ij

import com.intellij.ide.plugins.PluginManagerCore
import com.intellij.ide.util.PropertiesComponent
import com.intellij.notification.Notification
import com.intellij.notification.Notifications
import com.intellij.openapi.extensions.PluginId
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase

/** The announcement when a project becomes a Robot Framework project. */
class RobotCodeWhatsNewProjectTest : BasePlatformTestCase() {

    private val properties get() = PropertiesComponent.getInstance()
    private val announcer get() = RobotCodeUpdateAnnouncer.getInstance()
    private val environment get() = project.robotCodeEnvironment
    private var pluginVersion: String? = null

    override fun setUp() {
        super.setUp()
        // the activity that the platform creates hands over the version; afterwards the tests can replace it
        assertNotNull(platformStartupActivity())
        pluginVersion = announcer.pluginVersion
        environment.resetForTests()
        properties.unsetValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY)
    }

    override fun tearDown() {
        try {
            properties.unsetValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY)
            announcer.pluginVersion = pluginVersion
            environment.resetForTests()
        } catch (e: Throwable) {
            addSuppressedException(e)
        } finally {
            super.tearDown()
        }
    }

    fun testTheStartupActivityHandsOverTheVersionOfItsPlugin() {
        val descriptor = PluginManagerCore.getPlugin(PluginId.getId("dev.robotcode.robotcode4ij"))
        assertNotNull(descriptor)
        assertEquals(descriptor!!.version, announcer.pluginVersion)
    }

    fun testMarkingTheProjectAnnouncesANewVersionOnce() {
        announcer.pluginVersion = "2.8.0"
        properties.setValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY, "2.7.0")
        val notifications = collectWhatsNewNotifications()
        fun markRobotProject() {
            environment.markRobotProject()
            PlatformTestUtil.dispatchAllEventsInIdeEventQueue()
        }

        markRobotProject()
        assertEquals(1, notifications.size)
        assertTrue(notifications.single().content.contains("v2.8.0."))

        markRobotProject()
        assertEquals(1, notifications.size)

        environment.resetForTests()
        markRobotProject()
        assertEquals(1, notifications.size)
        assertEquals("2.8.0", properties.getValue(RobotCodeUpdateAnnouncer.LAST_VERSION_KEY))
    }

    private fun collectWhatsNewNotifications(): List<Notification> {
        val notifications = mutableListOf<Notification>()
        project.messageBus.connect(testRootDisposable).subscribe(Notifications.TOPIC, object : Notifications {
            override fun notify(notification: Notification) {
                if (notification.content.startsWith("RobotCode has been updated")) {
                    notifications += notification
                }
            }
        })
        return notifications
    }
}
