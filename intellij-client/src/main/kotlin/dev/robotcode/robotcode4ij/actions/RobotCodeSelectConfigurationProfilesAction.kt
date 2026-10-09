package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.Project
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.configuration.chooseProfiles
import dev.robotcode.robotcode4ij.editor.updateRobotCodeStatusBar
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged

/**
 * Tools | RobotCode | Select Configuration Profiles...: stores the selection at once, as VS Code's command does.
 */
class RobotCodeSelectConfigurationProfilesAction : AnAction() {
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val selection = RobotCodePersonalConfiguration.getInstance(project).profiles.toList()
        project.chooseProfiles(selection) { store(project, it) }?.let { store(project, it) }
    }

    private fun store(project: Project, profiles: List<String>) {
        val settings = RobotCodePersonalConfiguration.getInstance(project)
        if (profiles != settings.profiles) {
            settings.profiles = profiles.toMutableList()
            project.publishRobotCodeSettingsChanged()
            project.updateRobotCodeStatusBar()
        }
    }
}
