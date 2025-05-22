package dev.robotcode.robotcode4ij.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import dev.robotcode.robotcode4ij.lsp.langServerManager
import dev.robotcode.robotcode4ij.restartAll

class RobotCodeClearCacheAndRestartLanguageServerAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        e.project?.langServerManager?.clearCache()
        e.project?.restartAll(reset = true, debounced = false)
    }
}
