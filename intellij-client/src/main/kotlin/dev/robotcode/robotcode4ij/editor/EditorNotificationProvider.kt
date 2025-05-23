package dev.robotcode.robotcode4ij.editor

import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.fileEditor.FileEditor
import com.intellij.openapi.options.ShowSettingsUtil
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.ui.EditorNotificationPanel
import com.intellij.ui.EditorNotificationProvider
import dev.robotcode.robotcode4ij.CheckPythonAndRobotVersionResult
import dev.robotcode.robotcode4ij.RobotResourceFileType
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import dev.robotcode.robotcode4ij.checkPythonAndRobotVersion
import java.util.function.Function
import javax.swing.JComponent


@Suppress("DialogTitleCapitalization")
class EditorNotificationProvider : EditorNotificationProvider, DumbAware {
    override fun collectNotificationData(
        project: Project,
        file: VirtualFile
    ): Function<in FileEditor, out JComponent?>? {
        if (file.fileType == RobotSuiteFileType || file.fileType == RobotResourceFileType) {
            val result = project.checkPythonAndRobotVersion()
            if (result == CheckPythonAndRobotVersionResult.OK) {
                return null
            }
            
            return Function { editor ->
                val panel = EditorNotificationPanel(editor, EditorNotificationPanel.Status.Warning)
                panel.text = result.errorMessage ?: "RobotCode: Python and Robot Framework version check failed"
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
