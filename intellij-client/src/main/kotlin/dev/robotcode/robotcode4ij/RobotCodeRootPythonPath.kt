package dev.robotcode.robotcode4ij

import com.intellij.openapi.application.runReadActionBlocking
import com.intellij.openapi.module.Module
import com.intellij.openapi.module.ModuleUtilCore
import com.intellij.openapi.project.Project
import com.intellij.openapi.roots.ModuleRootEvent
import com.intellij.openapi.roots.ModuleRootListener
import com.intellij.openapi.roots.ModuleRootManager
import com.intellij.openapi.vfs.VirtualFile
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration

/** The roots of one module that the switches of the "Robot" page can put on the Python path, as paths. */
internal data class ModulePythonRoots(val contentRoots: List<String>, val sourceRoots: List<String>)

/**
 * The Python path entries for the roots of [modules], the module whose interpreter RobotCode uses first, then the
 * modules it depends on: all content roots before all source roots, as PyCharm's Python run configurations order them,
 * each folder once.
 */
internal fun rootPythonPathEntries(
    modules: List<ModulePythonRoots>, addContentRoots: Boolean, addSourceRoots: Boolean
): List<String> {
    val entries = LinkedHashSet<String>()
    if (addContentRoots) {
        modules.forEach { entries.addAll(it.contentRoots) }
    }
    if (addSourceRoots) {
        modules.forEach { entries.addAll(it.sourceRoots) }
    }
    return entries.toList()
}

/**
 * The Python path entries that the switches of the "Robot" page add: the content roots and the source roots, test
 * source roots included, of the module whose interpreter RobotCode uses and of the modules it depends on. The entries
 * of "Python path" come before them.
 */
internal fun Project.rootPythonPath(state: RobotCodeProjectConfiguration.ProjectState = robotSettings): List<String> {
    if (!state.robotAddContentRoots && !state.robotAddSourceRoots) {
        return emptyList()
    }
    // called from LSP4IJ's threads, the restart manager and the start of runs and discoveries
    return runReadActionBlocking {
        robotPythonModule?.let { rootPythonPath(it, state) }.orEmpty()
    }
}

/**
 * The Python path entries of the switches of the "Robot" page for [module] and the modules it depends on. It reads the
 * project model, so it runs in a read action.
 */
internal fun rootPythonPath(module: Module, state: RobotCodeProjectConfiguration.ProjectState): List<String> {
    // in the order of the dependencies, unlike PyCharm's hash set
    val modules = LinkedHashSet<Module>().also { ModuleUtilCore.getDependencies(module, it) }
    return rootPythonPathEntries(
        modules.map { dependency ->
            val roots = ModuleRootManager.getInstance(dependency)
            ModulePythonRoots(roots.contentRoots.localPaths(), roots.sourceRoots.localPaths())
        },
        state.robotAddContentRoots,
        state.robotAddSourceRoots
    )
}

private fun Array<VirtualFile>.localPaths(): List<String> = filter { it.isInLocalFileSystem }.map { it.path }

/**
 * Announces changes of the module roots and dependencies as a settings change: the restart manager compares what the
 * language server and the last discovery got, so only a change of the Python path restarts anything.
 */
class RobotCodeRootsListener(private val project: Project) : ModuleRootListener {
    override fun rootsChanged(event: ModuleRootEvent) {
        if (!project.isDefault) {
            project.publishRobotCodeSettingsChanged()
        }
    }
}
