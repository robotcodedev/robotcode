package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.DumbAware
import dev.robotcode.robotcode4ij.openWhatsNew

/**
 * Opens the news about the latest RobotCode release in the web browser, like VS Code's command "RobotCode: Show What's
 * New". It needs neither the language server nor a Robot Framework project, so it is always enabled.
 */
class RobotCodeShowWhatsNewAction : AnAction(), DumbAware {
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    override fun actionPerformed(e: AnActionEvent) {
        openWhatsNew()
    }
}
