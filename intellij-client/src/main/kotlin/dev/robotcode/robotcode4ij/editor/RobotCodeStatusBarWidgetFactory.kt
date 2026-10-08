package dev.robotcode.robotcode4ij.editor

import com.intellij.icons.AllIcons
import com.intellij.openapi.actionSystem.ActionGroup
import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.openapi.actionSystem.impl.SimpleDataContext
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.service
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.popup.JBPopup
import com.intellij.openapi.ui.popup.JBPopupFactory
import com.intellij.openapi.util.IconLoader
import com.intellij.openapi.util.NlsContexts
import com.intellij.openapi.util.text.StringUtil
import com.intellij.openapi.wm.StatusBarWidget
import com.intellij.openapi.wm.StatusBarWidgetFactory
import com.intellij.openapi.wm.WindowManager
import com.intellij.openapi.wm.impl.status.widget.StatusBarWidgetsManager
import com.intellij.ui.EditorNotifications
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.PythonInterpreter
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotCodeEnvironmentListener
import dev.robotcode.robotcode4ij.RobotIcons
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.isRobotCodeDisabled
import dev.robotcode.robotcode4ij.lsp.ProjectInfo
import dev.robotcode.robotcode4ij.lsp.robotCodeProjectInfo
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import org.jetbrains.annotations.NonNls
import javax.swing.Icon

/**
 * What the RobotCode widget shows: its text, the lines of its tooltip, and whether RobotCode cannot work.
 */
internal data class WidgetContent(val text: String, val tooltip: List<String>, val error: Boolean = false)

internal fun widgetContent(
    disabled: Boolean,
    state: EnvironmentState,
    info: ProjectInfo?,
    profiles: List<String>,
    interpreterPath: String?
): WidgetContent {
    val name = RobotCodeBundle.message("statusBar.name")
    return when {
        disabled -> WidgetContent(RobotCodeBundle.message("statusBar.off"), listOf(RobotCodeBundle.message("statusBar.disabled")))
        state is EnvironmentState.Failed || (state is EnvironmentState.Checked && !state.isUsable) ->
            WidgetContent(name, listOf(state.message), error = true)

        state !is EnvironmentState.Checked -> WidgetContent(name, listOf(state.message))
        info?.robotVersionString == null -> WidgetContent(name, listOf(RobotCodeBundle.message("statusBar.waiting")))
        else -> {
            val text = RobotCodeBundle.message("statusBar.robot", info.robotVersionString) +
                if (profiles.isEmpty()) "" else " · " + profiles.joinToString(", ")
            val tooltip = listOfNotNull(
                info.robotCodeVersionString?.let { RobotCodeBundle.message("statusBar.tooltip.robotCode", it) },
                RobotCodeBundle.message("statusBar.tooltip.robot", info.robotVersionString),
                info.robocopVersionString?.let { RobotCodeBundle.message("statusBar.tooltip.robocop", it) },
                info.pythonVersionString?.let {
                    RobotCodeBundle.message("statusBar.tooltip.python", it.substringBefore(' '))
                },
                (info.pythonExecutable ?: interpreterPath)?.let {
                    RobotCodeBundle.message("statusBar.tooltip.interpreter", it)
                },
                if (profiles.isEmpty()) {
                    RobotCodeBundle.message("statusBar.tooltip.defaultProfiles")
                } else {
                    RobotCodeBundle.message("statusBar.tooltip.profiles", profiles.joinToString(", "))
                }
            )
            WidgetContent(text, tooltip)
        }
    }
}

class RobotCodeStatusBarWidgetFactory : StatusBarWidgetFactory {
    companion object {
        // the id that plugin.xml registers the factory with
        const val ID = "dev.robotcode.robotcode4ij.editor.RobotCodeStatusBarWidget"
        private const val ACTION_GROUP = "dev.robotcode.robotcode4ij.actions"
    }

    override fun getId(): @NonNls String {
        return ID
    }

    override fun getDisplayName(): @NlsContexts.ConfigurableName String {
        return "Robot Framework"
    }

    // without bridges to the deprecated defaults of the presentation interfaces
    @JvmDefaultWithoutCompatibility
    class RobotCodeStatusBarWidget(private val project: Project) : StatusBarWidget,
                                                                   StatusBarWidget.MultipleTextValuesPresentation {
        override fun ID(): String {
            return ID
        }

        override fun getPresentation(): StatusBarWidget.WidgetPresentation = this

        private fun content(): WidgetContent {
            val environment = project.robotCodeEnvironment
            return widgetContent(
                project.isRobotCodeDisabled,
                environment.projectState,
                project.robotCodeProjectInfo.info,
                RobotCodePersonalConfiguration.getInstance(project).profiles.toList(),
                environment.projectInterpreter.homePath
            )
        }

        override fun getSelectedValue(): String = content().text

        override fun getTooltipText(): String {
            return "<html>" + content().tooltip.joinToString("<br>") { StringUtil.escapeXmlEntities(it) } + "</html>"
        }

        override fun getIcon(): Icon {
            return if (content().error) AllIcons.General.Error else IconLoader.getDarkIcon(RobotIcons.Resource, true)
        }

        // the RobotCode actions of Tools | RobotCode
        override fun getPopup(): JBPopup? {
            val group = ActionManager.getInstance().getAction(ACTION_GROUP) as? ActionGroup ?: return null
            return JBPopupFactory.getInstance().createActionGroupPopup(
                null, group, SimpleDataContext.getProjectContext(project),
                JBPopupFactory.ActionSelectionAid.SPEEDSEARCH, true
            )
        }
    }

    override fun createWidget(project: Project): StatusBarWidget {
        return RobotCodeStatusBarWidget(project)
    }

    // updated when the project is marked as one that uses Robot Framework
    override fun isAvailable(project: Project): Boolean {
        return project.robotCodeEnvironment.isRobotProject
    }
}

/**
 * Shows the result of the environment check in the banners of open Robot Framework files and in the status bar.
 */
class RobotCodeEnvironmentEditorListener(private val project: Project) : RobotCodeEnvironmentListener {
    override fun stateChanged(interpreter: PythonInterpreter, state: EnvironmentState) {
        EditorNotifications.getInstance(project).updateAllNotifications()
        project.updateRobotCodeStatusBar()
    }
}

/**
 * Decides again whether the status bar shows the RobotCode widget, and refreshes its text.
 */
internal fun Project.updateRobotCodeStatusBar() {
    ApplicationManager.getApplication().invokeLater({
        service<StatusBarWidgetsManager>().updateWidget(RobotCodeStatusBarWidgetFactory::class.java)
        WindowManager.getInstance().getStatusBar(this)?.updateWidget(RobotCodeStatusBarWidgetFactory.ID)
    }, disposed)
}
