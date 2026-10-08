package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import dev.robotcode.robotcode4ij.isRobotCodeDisabled
import dev.robotcode.robotcode4ij.setRobotCodeDisabled

/**
 * Unchecks "Disable extension"; shown only while it is checked.
 */
class RobotCodeEnableAction : AnAction() {
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible = e.project?.isRobotCodeDisabled == true
    }

    override fun actionPerformed(e: AnActionEvent) {
        e.project?.setRobotCodeDisabled(false)
    }
}
