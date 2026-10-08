package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import dev.robotcode.robotcode4ij.lsp.langServerManager

class RobotCodeClearCacheAndRestartLanguageServerAction : AnAction() {
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
    
    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }
    
    override fun actionPerformed(e: AnActionEvent) {
        e.project?.langServerManager?.clearCacheAndRestart()
    }
}
