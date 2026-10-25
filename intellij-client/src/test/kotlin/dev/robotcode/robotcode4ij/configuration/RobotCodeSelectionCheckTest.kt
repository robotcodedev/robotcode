package dev.robotcode.robotcode4ij.configuration

import com.intellij.testFramework.fixtures.BasePlatformTestCase

class RobotCodeSelectionCheckTest : BasePlatformTestCase() {

    private val check get() = project.selectionCheck

    private fun select(vararg names: String) {
        RobotCodePersonalConfiguration.getInstance(project).profiles = names.toMutableList()
    }

    // the project lives on to the next test, the selection and the notification of a test must not
    override fun tearDown() {
        try {
            check.notification?.expire()
            select()
        } finally {
            super.tearDown()
        }
    }

    fun testTheNotificationNamesTheProfileAndOffersTheFixes() {
        select("typo")

        check.report(listOf("typo"))

        val notification = check.notification!!
        assertEquals("RobotCode cannot find the selected profile", notification.title)
        assertEquals(
            "The selected profile \"typo\" is not defined in the configuration of this project.", notification.content
        )
        assertEquals(
            listOf("Remove from Selection", "Select Configuration Profiles..."),
            notification.actions.map { it.templatePresentation.text }
        )
    }

    fun testTheNotificationNamesSeveralProfiles() {
        select("typo", "ci-*")

        check.report(listOf("typo", "ci-*"))

        val notification = check.notification!!
        assertEquals("RobotCode cannot find the selected profiles", notification.title)
        assertEquals(
            "The selected profiles \"typo\", \"ci-*\" are not defined in the configuration of this project.",
            notification.content
        )
    }

    fun testOneNotificationPerSelection() {
        select("typo", "other")
        check.report(listOf("typo"))
        val first = check.notification!!

        // the same names show nothing new
        check.report(listOf("typo"))
        assertSame(first, check.notification)

        // other names replace it
        check.report(listOf("other"))
        assertTrue(first.isExpired)
        assertNotSame(first, check.notification)
    }

    fun testASelectionThatIsValidAgainExpiresTheNotification() {
        select("typo")
        check.report(listOf("typo"))
        val first = check.notification!!

        check.report(emptyList())

        assertTrue(first.isExpired)
        // the same name later shows a notification again
        check.report(listOf("typo"))
        assertNotSame(first, check.notification)
        assertFalse(check.notification!!.isExpired)
    }

    // such as a name of the extra arguments, or of a selection that has changed since the list was read
    fun testNamesThatTheSelectionDoesNotContainAreNotReported() {
        select("dev")

        check.report(listOf("typo"))

        assertTrue(check.notification?.isExpired ?: true)
    }
}
