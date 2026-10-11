package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Location
import com.intellij.execution.actions.ConfigurationContext
import com.intellij.execution.actions.ConfigurationFromContext
import com.intellij.execution.actions.LazyRunConfigurationProducer
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.actionSystem.PlatformCoreDataKeys
import com.intellij.openapi.fileTypes.FileTypeManager
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.roots.ProjectFileIndex
import com.intellij.openapi.roots.ProjectRootManager
import com.intellij.openapi.util.Ref
import com.intellij.openapi.vfs.VfsUtilCore
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.openapi.vfs.VirtualFileManager
import com.intellij.psi.PsiDirectory
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiManager
import com.intellij.psi.util.CachedValueProvider
import com.intellij.psi.util.CachedValuesManager
import com.redhat.devtools.lsp4ij.features.documentSymbol.DocumentSymbolData
import dev.robotcode.robotcode4ij.isRobotCodeDisabled
import dev.robotcode.robotcode4ij.psi.RobotSuiteFile
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.testManger
import java.nio.file.InvalidPathException
import java.nio.file.Path

fun DocumentSymbolData.toPsiElement(): PsiElement? {
    val file = this.containingFile
    return file.findElementAt(textOffset)
}

/**
 * The discovered item that a context run of [element] runs. Structure-view symbols keep their own item; any other
 * element runs the test or task whose body holds it, or the suite of its file or folder.
 */
private fun contextTestItem(project: Project, element: PsiElement): RobotCodeTestItem? {
    if (element is DocumentSymbolData) {
        return element.toPsiElement()?.let { project.testManger.findTestItem(it) }
    }
    return project.testManger.findContextTestItem(element)
}

/**
 * Whether a folder holds a suite file at any depth. The walk stops at the first one and skips hidden, ignored and
 * excluded folders. The result is kept until files or folders are added, removed or renamed or the project's roots
 * change, because the platform asks once for every existing configuration whenever it evaluates a context.
 */
private fun containsSuiteFile(folder: PsiDirectory): Boolean = CachedValuesManager.getCachedValue(folder) {
    val index = ProjectFileIndex.getInstance(folder.project)
    val fileTypes = FileTypeManager.getInstance()
    val found = !VfsUtilCore.iterateChildrenRecursively(folder.virtualFile, {
        !it.isDirectory || !(it.name.startsWith(".") || fileTypes.isFileIgnored(it) || index.isExcluded(it))
    }) {
        it.isDirectory || it.extension != "robot"
    }
    CachedValueProvider.Result.create(
        found, VirtualFileManager.VFS_STRUCTURE_MODIFICATIONS, ProjectRootManager.getInstance(folder.project)
    )
}

private fun VirtualFile.nioPath(): Path? = try {
    toNioPath()
} catch (_: UnsupportedOperationException) {
    null
}

/**
 * What a context run of [element] covers: its discovered item, or the path of a suite file or folder that discovery
 * does not know. An initialization file stands for its folder.
 */
private fun contextSelection(project: Project, element: PsiElement): ContextSelection? {
    val target = if (element is RobotSuiteFile && element.name == "__init__.robot") {
        element.containingDirectory ?: element
    } else {
        element
    }
    contextTestItem(project, target)?.let { return ContextSelection(it, null) }
    val file = when (target) {
        is PsiDirectory -> target.virtualFile.takeIf { containsSuiteFile(target) }
        else -> (target.containingFile as? RobotSuiteFile)?.virtualFile
    } ?: return null
    return ContextSelection(null, file.nioPath() ?: return null)
}

// the elements of a selection in the results tree, the Project view or the editor tabs
private fun selectedElements(project: Project, context: ConfigurationContext): List<PsiElement> {
    val data = context.dataContext
    data.getData(Location.DATA_KEYS)?.mapNotNull { it.psiElement }?.takeIf { it.isNotEmpty() }?.let { return it }
    data.getData(PlatformCoreDataKeys.PSI_ELEMENT_ARRAY)?.toList()?.takeIf { it.isNotEmpty() }?.let { return it }
    val psiManager = PsiManager.getInstance(project)
    return data.getData(CommonDataKeys.VIRTUAL_FILE_ARRAY).orEmpty().mapNotNull {
        if (it.isDirectory) psiManager.findDirectory(it) else psiManager.findFile(it)
    }
}

/**
 * What a context covers: every selected element when several are selected, else the [lead] element; each once and
 * without elements whose parent is selected too. Null when an element is not a Robot Framework suite, test or task.
 */
private fun contextSelections(
    project: Project, context: ConfigurationContext, lead: PsiElement?
): List<ContextSelection>? {
    val elements = if (context.containsMultipleSelection()) selectedElements(project, context) else listOfNotNull(lead)
    val selections = elements.map { contextSelection(project, it) ?: return null }
    return reduceSelections(selections, project.testManger.testItems).ifEmpty { null }
}

private fun workingDirectory(configuration: RobotCodeRunConfiguration): Path? = try {
    Path.of(configuration.workingDirectorySafe)
} catch (_: InvalidPathException) {
    null
}

/** Writes the target of [selections]: one item or path, or one target for several of them. */
private fun writeTarget(
    options: RobotCodeRunConfigurationOptions, selections: List<ContextSelection>, project: Project, base: Path?
): Boolean {
    val model = project.testManger.testItems
    val single = selections.singleOrNull()
    if (single?.item != null) {
        setContextTarget(options, single.item, model)
        return true
    }
    if (single?.path != null) {
        setPathTarget(options, single.path, base)
        return true
    }
    return setContextTargets(options, selections, model, base)
}

// reads the discovery result, the document and the file system, not the indexes, so it works while the IDE indexes
class RobotCodeRunConfigurationProducer : LazyRunConfigurationProducer<RobotCodeRunConfiguration>(), DumbAware {
    override fun getConfigurationFactory(): ConfigurationFactory {
        return runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
    }
    
    override fun setupConfigurationFromContext(
        configuration: RobotCodeRunConfiguration,
        context: ConfigurationContext,
        sourceElement: Ref<PsiElement>
    ): Boolean {
        val project = configuration.project
        if (project.isRobotCodeDisabled) {
            return false
        }
        val selections = contextSelections(project, context, sourceElement.get()) ?: return false
        if (!writeTarget(configuration.options, selections, project, workingDirectory(configuration))) {
            return false
        }
        configuration.setGeneratedName()
        return true
    }
    
    override fun isConfigurationFromContext(
        configuration: RobotCodeRunConfiguration,
        context: ConfigurationContext
    ): Boolean {
        val project = configuration.project
        if (project.isRobotCodeDisabled) {
            return false
        }
        val selections = contextSelections(project, context, context.psiLocation) ?: return false
        
        // compared by kind and name or path, so that line shifts and refreshed discovery items still match
        val expected = RobotCodeRunConfigurationOptions()
        return writeTarget(expected, selections, project, workingDirectory(configuration)) &&
            sameTarget(configuration.options, expected)
    }
    
    // neither this configuration nor pytest's is preferred, so the context menu keeps both; plugin.xml registers this
    // producer first, which lists the Robot Framework configuration first and lets Ctrl+Shift+F10 run it
    override fun isPreferredConfiguration(self: ConfigurationFromContext?, other: ConfigurationFromContext?): Boolean {
        return false
    }

}
