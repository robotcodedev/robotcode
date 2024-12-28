package dev.robotcode.robotcode4ij

import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity
import com.intellij.openapi.vfs.VirtualFileManager
import com.intellij.platform.backend.workspace.workspaceModel
import com.intellij.platform.workspace.jps.entities.ModuleEntity
import com.intellij.platform.workspace.storage.EntityChange
import dev.robotcode.robotcode4ij.lsp.langServerManager
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.flow.onEach

class RobotCodePostStartupActivity : ProjectActivity {
    override suspend fun execute(project: Project) {
        project.messageBus.connect().subscribe(VirtualFileManager.VFS_CHANGES, RobotCodeVirtualFileListener(project))
        
        project.langServerManager.start()
        
        project.workspaceModel.eventLog.onEach {
            val moduleChanges = it.getChanges(ModuleEntity::class.java)
            if (moduleChanges.filterIsInstance<EntityChange.Replaced<ModuleEntity>>().isNotEmpty()) {
                project.langServerManager.restart()
            }
        }.collect()
    }
    
   
}

