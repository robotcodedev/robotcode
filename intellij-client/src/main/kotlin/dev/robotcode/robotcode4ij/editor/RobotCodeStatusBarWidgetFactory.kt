package dev.robotcode.robotcode4ij.editor

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.IconLoader
import com.intellij.openapi.util.NlsContexts
import com.intellij.openapi.wm.StatusBarWidget
import com.intellij.openapi.wm.StatusBarWidget.IconPresentation
import com.intellij.openapi.wm.StatusBarWidgetFactory
import com.intellij.openapi.wm.impl.status.widget.StatusBarWidgetsManager
import com.intellij.ui.EditorNotifications
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.PythonInterpreter
import dev.robotcode.robotcode4ij.RobotCodeEnvironmentListener
import dev.robotcode.robotcode4ij.RobotIcons
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import org.jetbrains.annotations.NonNls

class RobotCodeStatusBarWidgetFactory : StatusBarWidgetFactory {
    override fun getId(): @NonNls String {
        return "RobotCodeStatusBarWidget"
    }
    
    override fun getDisplayName(): @NlsContexts.ConfigurableName String {
        return "Robot Framework"
    }
    
    class RobotCodeStatusBarWidget(project: Project) : StatusBarWidget {
        override fun ID(): String {
            return "dev.robotcode.robotcode4ij.editor.RobotCodeStatusBarWidget"
        }
        
        override fun getPresentation(): StatusBarWidget.WidgetPresentation? {
            return object : IconPresentation {
                override fun getIcon() = IconLoader.getDarkIcon(RobotIcons.Resource, true)
                override fun getTooltipText() = "RobotFramework"
                override fun getClickConsumer() = null
            }
        }
    }
    
    override fun createWidget(project: Project): StatusBarWidget {
        return RobotCodeStatusBarWidget(project)
    }
    
    // updated when the result of the check changes
    override fun isAvailable(project: Project): Boolean {
        return project.robotCodeEnvironment.projectState.isUsable
    }
}

/**
 * Shows the result of the environment check in the banners of open Robot Framework files and in the status bar.
 */
class RobotCodeEnvironmentEditorListener(private val project: Project) : RobotCodeEnvironmentListener {
    override fun stateChanged(interpreter: PythonInterpreter, state: EnvironmentState) {
        EditorNotifications.getInstance(project).updateAllNotifications()
        ApplicationManager.getApplication().invokeLater({
            project.service<StatusBarWidgetsManager>().updateWidget(RobotCodeStatusBarWidgetFactory::class.java)
        }, project.disposed)
    }
}
