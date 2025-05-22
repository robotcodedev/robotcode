package dev.robotcode.robotcode4ij

import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity
import com.intellij.openapi.vfs.VirtualFileManager
import com.intellij.platform.backend.workspace.workspaceModel
import com.intellij.platform.workspace.jps.entities.ModuleEntity
import com.intellij.platform.workspace.jps.entities.SdkEntity
import dev.robotcode.robotcode4ij.listeners.RobotCodeVirtualFileListener
import dev.robotcode.robotcode4ij.testing.testManger
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.onEach

class RobotCodePostStartupActivity : ProjectActivity {
    override suspend fun execute(project: Project) {
        project.restartAll(reset = true, debounced = false)
        
        VirtualFileManager.getInstance().addAsyncFileListener(RobotCodeVirtualFileListener(project), project.testManger)
        
        project.workspaceModel.eventLog.onEach {
            val sdkChanged = it.getChanges(SdkEntity::class.java).isNotEmpty()
            val moduleChanged = it.getChanges(ModuleEntity::class.java).isNotEmpty()
            
            if (moduleChanged || sdkChanged) {
                project.resetPythonAndRobotVersionCache()
                project.restartAll(reset = true)
            }
        }.collect()
    }
}

