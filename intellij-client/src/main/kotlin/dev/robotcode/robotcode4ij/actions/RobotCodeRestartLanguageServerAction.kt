package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import dev.robotcode.robotcode4ij.restartAll

class RobotCodeRestartLanguageServerAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        e.project?.restartAll(debounced = false)
    }
}
