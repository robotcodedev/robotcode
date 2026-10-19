package dev.robotcode.robotcode4ij

import com.intellij.ide.BrowserUtil
import com.intellij.ide.util.PropertiesComponent
import com.intellij.notification.NotificationAction
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import dev.robotcode.robotcode4ij.configuration.RobotCodeApplicationConfiguration

/**
 * The page that VS Code's "What's New?" opens too; the docs site redirects it to the news post of the latest release.
 */
internal const val WHATS_NEW_URL = "https://robotcode.io/news/latest/"

private const val NOTIFICATION_GROUP = "RobotCode"

/**
 * Announces RobotCode's version in this project, unless the IDE noted it already. Called when the project becomes a
 * Robot Framework project and when the startup activity has run in one. Without a known version it does nothing.
 */
internal fun Project.announceNewVersion() {
    val announcer = RobotCodeUpdateAnnouncer.getInstance()
    val version = announcer.pluginVersion ?: return
    if (announcer.noteVersion(version)) {
        showWhatsNewNotification(this, version)
    }
}

/**
 * Opens the news about the latest release in the web browser that the IDE uses.
 */
internal fun openWhatsNew() {
    BrowserUtil.browse(WHATS_NEW_URL)
}

/**
 * Tells the user that RobotCode was updated to [version], with VS Code's text and its action "What's New?".
 */
internal fun showWhatsNewNotification(project: Project, version: String) {
    NotificationGroupManager.getInstance().getNotificationGroup(NOTIFICATION_GROUP)
        .createNotification(RobotCodeBundle.message("whatsNew.notification", version), NotificationType.INFORMATION)
        .addAction(
            NotificationAction.createSimpleExpiring(RobotCodeBundle.message("whatsNew.action")) { openWhatsNew() }
        )
        .notify(project)
}

/**
 * Whether [version] is a dev build: a semver pre-release such as `2.8.0-dev.508`, as the CI builds them for the
 * Marketplace channel `dev`. Build metadata after `+` doesn't make a version a dev build.
 */
internal fun isDevBuild(version: String): Boolean = version.substringBefore('+').contains('-')

/**
 * Whether the plugin announces [version] when it noted [noted] the last time: any other version, also when none was
 * noted yet or for a downgrade, as in VS Code, unless it is a dev build or "Show whats new on update" is off.
 */
internal fun shouldAnnounce(noted: String?, version: String, enabled: Boolean): Boolean {
    return enabled && noted != version && !isDevBuild(version)
}

/**
 * Notes the version of RobotCode for the IDE installation and decides whether to announce it. The noted version doesn't
 * roam with Settings Sync, like VS Code's global state, so another machine still announces its own update.
 */
@Service(Service.Level.APP)
internal class RobotCodeUpdateAnnouncer {
    companion object {
        // the key of VS Code's global state
        const val LAST_VERSION_KEY = "robotcode.lastVersion"

        // outside of extension functions on Project, so that service() is the application's
        fun getInstance(): RobotCodeUpdateAnnouncer = service()
    }

    /**
     * The version of the RobotCode plugin, from the descriptor that the platform hands to the startup activity;
     * `PluginManagerCore.getPlugin` is internal API since 2026.2.
     */
    @Volatile
    var pluginVersion: String? = null

    /**
     * Notes [version], whatever the decision, and returns whether to announce it. Only the call that changes the noted
     * version can announce, so projects that open at the same time announce a version once.
     */
    @Synchronized
    fun noteVersion(version: String): Boolean {
        val properties = PropertiesComponent.getInstance()
        val noted = properties.getValue(LAST_VERSION_KEY)
        properties.setValue(LAST_VERSION_KEY, version)
        return shouldAnnounce(noted, version, RobotCodeApplicationConfiguration.getInstance().showWhatsNewOnUpdate)
    }
}
