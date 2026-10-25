package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import dev.robotcode.robotcode4ij.configuration.selectConfigurationProfiles

/**
 * Tools | RobotCode | Select Configuration Profiles...: stores the selection at once, as VS Code's command does.
 */
class RobotCodeSelectConfigurationProfilesAction : AnAction() {
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        e.project?.selectConfigurationProfiles()
    }
}
