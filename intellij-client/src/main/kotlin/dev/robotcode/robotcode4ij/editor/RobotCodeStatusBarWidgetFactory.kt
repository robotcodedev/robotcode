package dev.robotcode.robotcode4ij.editor

import com.intellij.openapi.project.Project
import com.intellij.openapi.util.IconLoader
import com.intellij.openapi.util.NlsContexts
import com.intellij.openapi.wm.StatusBarWidget
import com.intellij.openapi.wm.StatusBarWidget.IconPresentation
import com.intellij.openapi.wm.StatusBarWidgetFactory
import dev.robotcode.robotcode4ij.CheckPythonAndRobotVersionResult
import dev.robotcode.robotcode4ij.RobotIcons
import dev.robotcode.robotcode4ij.checkPythonAndRobotVersion
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
    
    override fun isAvailable(project: Project): Boolean {
        return project.checkPythonAndRobotVersion() == CheckPythonAndRobotVersionResult.OK
    }
}
