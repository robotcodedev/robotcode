package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.wm.ToolWindowManager

/**
 * Opens LSP4IJ's Language Servers tool window, which shows the output of the RobotCode language server.
 */
class RobotCodeShowLanguageServerLogAction : AnAction() {
    companion object {
        private const val LANGUAGE_SERVERS_TOOL_WINDOW = "Language Servers"
    }

    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        ToolWindowManager.getInstance(project).getToolWindow(LANGUAGE_SERVERS_TOOL_WINDOW)?.activate(null)
    }
}
