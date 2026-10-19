package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.wm.ToolWindowManager
import com.redhat.devtools.lsp4ij.LanguageServersRegistry
import com.redhat.devtools.lsp4ij.console.LSPConsoleToolWindowPanel
import dev.robotcode.robotcode4ij.lsp.RobotCodeLanguageServerManager

/**
 * Opens LSP4IJ's Language Servers tool window at the Logs tab of the running RobotCode language server, which shows the
 * output of the server.
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
        val toolWindow = ToolWindowManager.getInstance(project).getToolWindow(LANGUAGE_SERVERS_TOOL_WINDOW) ?: return
        toolWindow.activate {
            // selects the server's running process and its Logs tab; without a running server, nothing is selected
            LanguageServersRegistry.getInstance().getServerDefinition(RobotCodeLanguageServerManager.LANGUAGE_SERVER_ID)
                ?.let { LSPConsoleToolWindowPanel.selectLogTab(it, project) }
        }
    }
}
