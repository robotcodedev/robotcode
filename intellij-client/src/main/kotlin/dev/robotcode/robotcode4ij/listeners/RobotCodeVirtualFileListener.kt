package dev.robotcode.robotcode4ij.listeners

import com.intellij.openapi.project.Project
import com.intellij.openapi.roots.ProjectFileIndex
import com.intellij.openapi.util.io.FileUtil
import com.intellij.openapi.vfs.AsyncFileListener
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.openapi.vfs.newvfs.events.VFileCreateEvent
import com.intellij.openapi.vfs.newvfs.events.VFileEvent
import com.intellij.openapi.vfs.newvfs.events.VFileMoveEvent
import com.intellij.openapi.vfs.newvfs.events.VFilePropertyChangeEvent
import com.intellij.util.PathUtil
import dev.robotcode.robotcode4ij.restartAll
import dev.robotcode.robotcode4ij.restartLanguageServer

/** What a change of a configuration file needs. */
internal enum class ConfigFileWork { SERVER, SERVER_AND_DISCOVERY }

/**
 * Robocop's configuration is read only by the language server; the other files are read by the server and by discovery.
 */
internal fun configFileWork(name: String): ConfigFileWork? {
    return when (name) {
        "robocop.toml" -> ConfigFileWork.SERVER
        "robot.toml", ".robot.toml", "pyproject.toml", ".gitignore", ".robotignore" -> ConfigFileWork.SERVER_AND_DISCOVERY
        else -> null
    }
}

/**
 * Whether the file of [event] is in the project's content or below the project folder. Decided before the change, while
 * a deleted file still exists.
 */
internal fun Project.ownsEvent(event: VFileEvent): Boolean {
    if (isDisposed) {
        return false
    }
    val index = ProjectFileIndex.getInstance(this)
    val files = listOfNotNull(event.file, (event as? VFileCreateEvent)?.parent, (event as? VFileMoveEvent)?.newParent)
    if (files.any { it.isValid && index.isInContent(it) }) {
        return true
    }
    val base = basePath ?: return false
    return FileUtil.isAncestor(base, event.path, false)
}

// the names before and after a rename
private fun eventNames(event: VFileEvent): List<String> {
    val renamed = (event as? VFilePropertyChangeEvent)?.takeIf { it.propertyName == VirtualFile.PROP_NAME }?.newValue
    return listOfNotNull(PathUtil.getFileName(event.path), renamed as? String)
}

class RobotCodeVirtualFileListener(private val project: Project) : AsyncFileListener {

    /**
     * The work that [events] need, from the configuration files of this project only.
     */
    internal fun requestedWork(events: List<VFileEvent>): ConfigFileWork? {
        var work: ConfigFileWork? = null
        for (event in events) {
            val fileWork = eventNames(event).mapNotNull { configFileWork(it) }.maxOrNull() ?: continue
            if (!project.ownsEvent(event)) {
                continue
            }
            if (fileWork == ConfigFileWork.SERVER_AND_DISCOVERY) {
                return fileWork
            }
            work = fileWork
        }
        return work
    }

    override fun prepareChange(events: List<VFileEvent>): AsyncFileListener.ChangeApplier? {
        val work = requestedWork(events) ?: return null
        return object : AsyncFileListener.ChangeApplier {
            override fun afterVfsChange() {
                when (work) {
                    ConfigFileWork.SERVER -> project.restartLanguageServer()
                    ConfigFileWork.SERVER_AND_DISCOVERY -> project.restartAll()
                }
            }
        }
    }
}
