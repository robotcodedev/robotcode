package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.ActionUpdateThread
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import dev.robotcode.robotcode4ij.restartAll

class RobotCodeRestartLanguageServerAction : AnAction() {
    override fun getActionUpdateThread(): ActionUpdateThread = ActionUpdateThread.BGT
    
    override fun update(e: AnActionEvent) {
        e.presentation.isEnabled = e.project != null
    }
    
    // checks the environment again, so that an interpreter fixed outside the IDE is picked up
    override fun actionPerformed(e: AnActionEvent) {
        e.project?.restartAll(reset = true)
    }
}
