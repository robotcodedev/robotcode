package dev.robotcode.robotcode4ij

import com.intellij.ide.lightEdit.LightEdit
import com.intellij.openapi.application.smartReadAction
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.fileEditor.FileEditorManagerListener
import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.openapi.vfs.VirtualFileManager
import com.intellij.psi.search.FileTypeIndex
import com.intellij.psi.search.FilenameIndex
import com.intellij.psi.search.GlobalSearchScope
import dev.robotcode.robotcode4ij.listeners.RobotCodeVirtualFileListener
import dev.robotcode.robotcode4ij.testing.testManger

class RobotCodePostStartupActivity : ProjectActivity {
    override suspend fun execute(project: Project) {
        if (project.isDefault || LightEdit.owns(project)) {
            return
        }

        VirtualFileManager.getInstance().addAsyncFileListener(RobotCodeVirtualFileListener(project), project.testManger)

        val environment = project.robotCodeEnvironment
        environment.watchWorkspaceModel()

        // in any other project, RobotCode starts when the first Robot Framework file is opened
        if (smartReadAction(project) { containsRobotFrameworkFiles(project) }) {
            environment.markRobotProject()
        }
    }
}

/**
 * Whether the project contains Robot Framework suite or resource files, or a `robot.toml` or `.robot.toml`.
 */
internal fun containsRobotFrameworkFiles(project: Project): Boolean {
    val scope = GlobalSearchScope.projectScope(project)
    return FileTypeIndex.containsFileOfType(RobotSuiteFileType, scope) ||
        FileTypeIndex.containsFileOfType(RobotResourceFileType, scope) ||
        listOf("robot.toml", ".robot.toml").any { FilenameIndex.getVirtualFilesByName(it, scope).isNotEmpty() }
}

/**
 * Marks the project as a Robot Framework project when a Robot Framework file is opened.
 */
class RobotCodeFileOpenedListener(private val project: Project) : FileEditorManagerListener {
    override fun fileOpened(source: FileEditorManager, file: VirtualFile) {
        if (file.fileType == RobotSuiteFileType || file.fileType == RobotResourceFileType) {
            project.robotCodeEnvironment.markRobotProject()
        }
    }
}
