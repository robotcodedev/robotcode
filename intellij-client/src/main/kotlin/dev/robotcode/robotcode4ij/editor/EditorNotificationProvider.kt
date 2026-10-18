package dev.robotcode.robotcode4ij.editor

import com.intellij.openapi.fileEditor.FileEditor
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.text.StringUtil
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.ui.EditorNotificationPanel
import com.intellij.ui.EditorNotificationProvider
import com.intellij.ui.EditorNotifications
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotResourceFileType
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import dev.robotcode.robotcode4ij.actions.RobotCodeConfigurePythonInterpreterAction
import dev.robotcode.robotcode4ij.isRobotCodeDisabled
import dev.robotcode.robotcode4ij.restartAll
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import dev.robotcode.robotcode4ij.setRobotCodeDisabled
import org.jetbrains.annotations.TestOnly
import java.util.concurrent.ConcurrentHashMap
import java.util.function.Function
import javax.swing.JComponent

/**
 * The text of the banner for an interpreter that RobotCode cannot use: the result of the check. It names what is
 * missing, not how to install it; which tool and which version a project uses for that is the project's decision.
 */
internal fun bannerText(state: EnvironmentState): String = "<html>" + StringUtil.escapeXmlEntities(state.message) + "</html>"

@Suppress("DialogTitleCapitalization")
class EditorNotificationProvider : EditorNotificationProvider, DumbAware {
    companion object {
        // the projects whose banner the user closed, until the IDE restarts
        private val dismissed = ConcurrentHashMap.newKeySet<String>()

        @TestOnly
        internal fun clearDismissedForTests() {
            dismissed.clear()
        }
    }

    override fun collectNotificationData(
        project: Project,
        file: VirtualFile
    ): Function<in FileEditor, out JComponent?>? {
        val robotFile = file.fileType == RobotSuiteFileType || file.fileType == RobotResourceFileType
        if (!robotFile || project.isRobotCodeDisabled || project.locationHash in dismissed) {
            return null
        }

        // never waits for the check; the banner is updated when the result arrives
        val environment = project.robotCodeEnvironment
        val interpreter = environment.projectInterpreter
        val state = environment.state(interpreter)
        if (state == EnvironmentState.Unknown) {
            environment.requestCheck(interpreter)
        }
        if ((state !is EnvironmentState.Checked && state !is EnvironmentState.Failed) || state.isUsable) {
            return null
        }

        return Function { editor ->
            val panel = EditorNotificationPanel(editor, EditorNotificationPanel.Status.Warning)
            panel.text = bannerText(state)
            panel.createActionLabel(RobotCodeBundle.message("python.banner.configure")) {
                RobotCodeConfigurePythonInterpreterAction.showPythonInterpreterSettings(project)
            }
            panel.createActionLabel(RobotCodeBundle.message("python.banner.retry")) {
                project.restartAll(reset = true)
            }
            panel.createActionLabel(RobotCodeBundle.message("python.banner.disable")) {
                project.setRobotCodeDisabled(true)
            }
            panel.setCloseAction {
                dismissed.add(project.locationHash)
                EditorNotifications.getInstance(project).updateAllNotifications()
            }
            panel
        }
    }
}
