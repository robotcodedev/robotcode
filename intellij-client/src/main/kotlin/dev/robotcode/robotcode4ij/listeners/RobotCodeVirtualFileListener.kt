package dev.robotcode.robotcode4ij.listeners

import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.AsyncFileListener
import com.intellij.openapi.vfs.newvfs.events.VFileEvent
import dev.robotcode.robotcode4ij.restartAll

class RobotCodeVirtualFileListener(private val project: Project) : AsyncFileListener {
    companion object {
        val PROJECT_FILES = arrayOf("robot.toml", ".robot.toml", "pyproject.toml", "robocop.toml")
    }

    override fun prepareChange(events: List<VFileEvent>): AsyncFileListener.ChangeApplier? {
        return object : AsyncFileListener.ChangeApplier {
            override fun afterVfsChange() {
                if (events.any { it.file?.name in PROJECT_FILES }) {
                    project.restartAll()
                }
            }
        }
    }
}
