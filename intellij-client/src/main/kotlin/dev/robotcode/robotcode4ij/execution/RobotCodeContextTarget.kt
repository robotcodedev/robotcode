package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import java.nio.file.InvalidPathException
import java.nio.file.Path
import java.util.Locale
import kotlin.io.path.exists

/**
 * One selected element of a context run: a discovered [item], or the [path] of a suite file or folder that discovery
 * does not know.
 */
internal data class ContextSelection(val item: RobotCodeTestItem?, val path: Path?) {
    // the file or folder of the selection
    val location: Path?
        get() = path ?: item?.source?.let {
            try {
                Path.of(it)
            } catch (_: InvalidPathException) {
                null
            }
        }
}

/** The ids of the discovered items above each item of [model]. */
internal fun ancestorIds(model: Array<RobotCodeTestItem>): Map<String, Set<String>> {
    val result = mutableMapOf<String, Set<String>>()
    fun visit(item: RobotCodeTestItem, above: Set<String>) {
        result[item.id] = above
        item.children?.forEach { visit(it, above + item.id) }
    }
    model.forEach { visit(it, emptySet()) }
    return result
}

// whether [parent] holds [child]: a discovered item above it, or a folder that contains its file or folder
private fun covers(parent: ContextSelection, child: ContextSelection, ancestors: Map<String, Set<String>>): Boolean {
    val parentId = parent.item?.id
    val childId = child.item?.id
    if (parentId != null && childId != null) {
        return parentId in ancestors[childId].orEmpty()
    }
    val parentPath = parent.location?.normalize() ?: return false
    val childPath = child.location?.normalize() ?: return false
    return childPath != parentPath && childPath.startsWith(parentPath)
}

/**
 * The selections that a context run of several elements covers: each once, and none whose discovered parent or folder
 * is selected as well.
 */
internal fun reduceSelections(
    selections: List<ContextSelection>, model: Array<RobotCodeTestItem>
): List<ContextSelection> {
    val unique = selections.distinctBy { it.item?.id ?: it.location?.normalize()?.toString() }
    // one selection covers no other, and the platform asks once for every existing configuration, so the ancestors of
    // the whole model are only built for several selections
    if (unique.size < 2) {
        return unique
    }
    val ancestors = ancestorIds(model)
    return unique.filter { selection -> unique.none { it !== selection && covers(it, selection, ancestors) } }
}

/**
 * Writes the target of a context run of several [selections] into [options]: "Tests and suites" when discovery knows
 * every selection, and "Files and folders" when every selection is a file or folder, with the paths relative to the
 * working directory [base]. Any other mix gets no target, and the result is false.
 */
internal fun setContextTargets(
    options: RobotCodeRunConfigurationOptions,
    selections: List<ContextSelection>,
    model: Array<RobotCodeTestItem>,
    base: Path?
): Boolean {
    if (selections.isEmpty()) {
        return false
    }
    val items = selections.mapNotNull { selection -> selection.item?.let { selectionItemOf(it, model) } }
    if (items.size == selections.size) {
        options.targetKind = RobotRunTargetKind.SELECTION
        options.targetPaths = mutableListOf()
        options.selection = items.map { it.second }.toMutableList()
        options.topLevelSuite = items.first().first
        return true
    }
    if (selections.all { it.item == null || it.item.type == "suite" }) {
        val paths = selections.map { it.location ?: return false }
        options.targetKind = RobotRunTargetKind.PATHS
        options.targetPaths = paths.map { pathRelativeTo(it, base) }.toMutableList()
        options.selection = mutableListOf()
        options.topLevelSuite = null
        return true
    }
    return false
}

/** Writes the target of a context run of a file or folder that discovery does not know: its path. */
internal fun setPathTarget(options: RobotCodeRunConfigurationOptions, path: Path, base: Path?) {
    options.targetKind = RobotRunTargetKind.PATHS
    options.targetPaths = mutableListOf(pathRelativeTo(path, base))
    options.selection = mutableListOf()
    options.topLevelSuite = null
}

/**
 * Whether two targets name the same items for gutter and context runs: the same kind and the same items or paths, in
 * any order.
 */
internal fun sameTarget(first: RobotCodeRunConfigurationOptions, second: RobotCodeRunConfigurationOptions): Boolean {
    val (firstKind, firstItems) = targetKey(first)
    val (secondKind, secondItems) = targetKey(second)
    return firstKind == secondKind && firstItems.toSet() == secondItems.toSet()
}

/** A stored path, resolved against the working directory [base] when it is relative. */
internal fun resolveStoredPath(path: String, base: Path?): Path? = try {
    (base?.resolve(path) ?: Path.of(path)).normalize()
} catch (_: InvalidPathException) {
    null
}

/**
 * The stored [paths] of a "Files and folders" target that do not exist, each after [expand], which returns null for a
 * path whose macros cannot be expanded without a run, and resolved against the working directory [base].
 */
internal fun missingTargetPaths(paths: List<String>, base: Path?, expand: (String) -> String?): List<String> {
    return paths.filter { it.isNotBlank() }.filter { path ->
        expand(path)?.let { resolveStoredPath(it, base) }?.exists() == false
    }
}

/**
 * The name of a configuration created from context, from its target: "<Type> <name>" for one discovered item, "Robot
 * <name>" for one file or folder, "Robot: <n> items" for several, and "Workspace <name>" for the project folder, named
 * [projectFolder]. Relative paths count from the working directory [base].
 */
internal fun targetName(options: RobotCodeRunConfigurationOptions, projectFolder: String?, base: Path?): String? {
    return when (options.targetKind) {
        RobotRunTargetKind.SELECTION -> {
            val item = options.selection.singleOrNull()
                ?: return options.selection.takeIf { it.isNotEmpty() }?.let { "Robot: ${it.size} items" }
            // entries of earlier versions have no own name
            val name = item.label ?: item.name?.substringAfterLast('.') ?: return null
            val kind = item.kind ?: return "Robot $name"
            "${kind.replaceFirstChar { it.titlecase(Locale.ROOT) }} $name"
        }
        RobotRunTargetKind.PATHS -> when (options.targetPaths.size) {
            0 -> projectFolder?.let { "Workspace $it" }
            1 -> {
                val path = options.targetPaths.single()
                "Robot ${resolveStoredPath(path, base)?.fileName ?: path}"
            }
            else -> "Robot: ${options.targetPaths.size} items"
        }
    }
}
