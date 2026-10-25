package dev.robotcode.robotcode4ij.configuration

import com.intellij.notification.Notification
import com.intellij.notification.NotificationAction
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.text.StringUtil
import dev.robotcode.robotcode4ij.RobotCodeBundle
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import org.jetbrains.annotations.VisibleForTesting

/**
 * The names of the project's selection that select no profile of `robot.toml`, as `robotcode profiles list` reports
 * them; none when the list cannot be read. The list also names the names of other `-p` options, such as those of the
 * extra arguments, which are no part of the selection.
 */
internal suspend fun Project.unknownSelectedProfiles(): List<String> {
    val selection = RobotCodePersonalConfiguration.getInstance(this).profiles.toList()
    if (selection.isEmpty()) {
        return emptyList()
    }
    val unknown = (readProfileListInBackground(selection) as? ProfileListResult.Read)?.list?.unknownSelected.orEmpty()
    return unknown.filter { it in selection }
}

/**
 * Reports the names of the project's selection that select no profile, with the actions that fix the selection. The
 * platform cancels the scope when the project closes or the plugin is unloaded.
 */
@Service(Service.Level.PROJECT)
internal class RobotCodeSelectionCheck(private val project: Project, private val scope: CoroutineScope) {

    @VisibleForTesting
    internal var notification: Notification? = null
        private set

    private var reported: List<String> = emptyList()

    private var check: Job? = null

    /**
     * Reads the profile list with the selection in the background and reports what it names, after a server start. A
     * check of an earlier start that is still running is cancelled.
     */
    @Synchronized
    fun check() {
        check?.cancel()
        check = scope.launch { report(project.unknownSelectedProfiles()) }
    }

    /**
     * Shows one notification for those of [names] that the selection still contains, on the EDT: the same names again
     * show nothing new, other ones replace it, and none expire it, so a selection that is valid again leaves none.
     */
    fun report(names: List<String>) {
        val application = ApplicationManager.getApplication()
        if (!application.isDispatchThread) {
            application.invokeLater({ report(names) }, project.disposed)
            return
        }
        // a result about an older selection names nothing that the selection still contains
        val selection = RobotCodePersonalConfiguration.getInstance(project).profiles
        val current = names.filter { it in selection }
        if (current.isEmpty()) {
            notification?.expire()
            reported = emptyList()
            return
        }
        if (current == reported && notification?.isExpired == false) {
            return
        }
        notification?.expire()
        reported = current
        val quoted = current.joinToString(", ") { "\"${StringUtil.escapeXmlEntities(it)}\"" }
        val notification = NotificationGroupManager.getInstance().getNotificationGroup(NOTIFICATION_GROUP)
            .createNotification(
                RobotCodeBundle.message("profiles.unknown.title", current.size),
                RobotCodeBundle.message("profiles.unknown.text", quoted, current.size),
                NotificationType.ERROR
            )
        notification.addAction(NotificationAction.createSimpleExpiring(RobotCodeBundle.message("profiles.unknown.remove")) {
            val profiles = RobotCodePersonalConfiguration.getInstance(project).profiles
            project.storeProfileSelection(profiles.filter { it !in current })
        })
        notification.addAction(NotificationAction.createSimpleExpiring(RobotCodeBundle.message("profiles.unknown.select")) {
            project.selectConfigurationProfiles()
        })
        this.notification = notification
        notification.notify(project)
    }

    private companion object {
        private const val NOTIFICATION_GROUP = "RobotCode"
    }
}

/** The check of the project's profile selection. */
internal val Project.selectionCheck: RobotCodeSelectionCheck
    get() = service<RobotCodeSelectionCheck>()
