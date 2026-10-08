package dev.robotcode.robotcode4ij.editor

import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.fileEditor.FileEditor
import com.intellij.openapi.options.ShowSettingsUtil
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.ui.EditorNotificationPanel
import com.intellij.ui.EditorNotificationProvider
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.RobotResourceFileType
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import java.util.function.Function
import javax.swing.JComponent


@Suppress("DialogTitleCapitalization")
class EditorNotificationProvider : EditorNotificationProvider, DumbAware {
    override fun collectNotificationData(
        project: Project,
        file: VirtualFile
    ): Function<in FileEditor, out JComponent?>? {
        if (file.fileType == RobotSuiteFileType || file.fileType == RobotResourceFileType) {
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
                panel.text = state.message
                panel.createActionLabel("Configure Python Interpreter") {
                    
                    ShowSettingsUtil.getInstance().showSettingsDialog(project, "Python Interpreter")
                }
                panel.setCloseAction {
                    thisLogger().info("Close action clicked")
                }
                panel
            }
        }
        return null
    }
    
}
