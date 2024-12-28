package dev.robotcode.robotcode4ij

import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.newvfs.BulkFileListener
import com.intellij.openapi.vfs.newvfs.events.VFileEvent
import dev.robotcode.robotcode4ij.lsp.langServerManager

class RobotCodeVirtualFileListener(private val project: Project) : BulkFileListener {
    companion object {
        val PROJECT_FILES = arrayOf("robot.toml", ".robot.toml", "pyproject.toml")
    }
    
    override fun after(events: MutableList<out VFileEvent>) {
        if (events.any { it.file?.name in PROJECT_FILES }) {
            project.langServerManager.restart()
        }
    }
}
