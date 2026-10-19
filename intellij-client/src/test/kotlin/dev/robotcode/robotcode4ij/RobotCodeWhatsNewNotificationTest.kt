package dev.robotcode.robotcode4ij

import com.intellij.notification.Notification
import com.intellij.notification.Notifications
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase

class RobotCodeWhatsNewNotificationTest : BasePlatformTestCase() {

    private fun collectNotifications(): MutableList<Notification> {
        val notifications = mutableListOf<Notification>()
        project.messageBus.connect(testRootDisposable).subscribe(Notifications.TOPIC, object : Notifications {
            override fun notify(notification: Notification) {
                notifications += notification
            }
        })
        return notifications
    }

    fun testNotificationNamesTheVersionAndOpensTheNews() {
        val browser = RecordingBrowserLauncher.install(testRootDisposable)
        val notifications = collectNotifications()

        showWhatsNewNotification(project, "2.8.0")
        PlatformTestUtil.dispatchAllEventsInIdeEventQueue()

        val notification = notifications.single()
        assertEquals("RobotCode", notification.groupId)
        assertEquals(
            "RobotCode has been updated to v2.8.0. Want to know what's new? Click below to see all the latest " +
                "changes and improvements.",
            notification.content
        )
        val action = notification.actions.single()
        assertEquals("What's New?", action.templateText)

        Notification.fire(notification, action, null)

        assertEquals(listOf("https://robotcode.io/news/latest/"), browser.urls)
        assertTrue(notification.isExpired)
    }
}
