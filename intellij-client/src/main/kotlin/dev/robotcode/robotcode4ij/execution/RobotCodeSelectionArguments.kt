package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.utils.escapeRobotGlob

/**
 * What a run passes for one selected item: its full name for `-bl`, and the full name and the file or folder of its
 * suite for `-s` and `-I`.
 */
internal data class SelectionEntry(val longname: String, val suite: String?, val relSource: String?)

/** A selection resolved against the discovery model. Without entries, the run covers the whole project. */
internal data class ResolvedSelection(val topLevelSuite: String?, val entries: List<SelectionEntry>)

private fun RobotCodeTestItem.withDescendants(): Sequence<RobotCodeTestItem> = sequence {
    yield(this@withDescendants)
    children?.forEach { yieldAll(it.withDescendants()) }
}

/**
 * Resolves the [selected] items of a run against the current discovery [model]. The items can be older than the model,
 * so the suite of a test or task is the file suite with the same URI in the model; a suite stands for itself. An empty
 * selection, the workspace item or the top-level suite cover the whole project.
 */
internal fun resolveSelection(selected: List<RobotCodeTestItem>, model: Array<RobotCodeTestItem>): ResolvedSelection {
    val topLevel = model.firstOrNull()?.children?.firstOrNull()
    if (selected.isEmpty() || selected.any { it.type == "workspace" || it.id == topLevel?.id }) {
        return ResolvedSelection(null, emptyList())
    }
    val suites = model.asSequence().flatMap { it.withDescendants() }.filter { it.type == "suite" }.toList()
    val entries = selected.map { item ->
        if (item.type == "test" || item.type == "task") {
            val suite = suites.firstOrNull { it.isSameUri(item.uri) }
            SelectionEntry(item.longname, suite?.longname, suite?.relSource ?: item.relSource)
        } else {
            SelectionEntry(item.longname, item.longname, item.relSource)
        }
    }
    return ResolvedSelection(topLevel?.longname, entries)
}

/**
 * The stored item for a discovery [item] that a gutter or context run selected, with the name of the top-level suite,
 * as discovery reports them, or null when the item covers the whole project.
 */
internal fun selectionItemOf(
    item: RobotCodeTestItem, model: Array<RobotCodeTestItem>
): Pair<String?, RobotRunSelectionItem>? {
    val resolved = resolveSelection(listOf(item), model)
    val entry = resolved.entries.singleOrNull() ?: return null
    val topLevel = resolved.topLevelSuite
    return topLevel to RobotRunSelectionItem().apply {
        kind = item.type
        name = entry.longname
        relSource = item.relSource
        suite = entry.suite
        suiteRelSource = entry.relSource
    }
}

/**
 * Writes the target that a gutter or context run of [item] gets: its stored item, or no paths when the item covers the
 * whole project.
 */
internal fun setContextTarget(
    options: RobotCodeRunConfigurationOptions, item: RobotCodeTestItem, model: Array<RobotCodeTestItem>
) {
    val selected = selectionItemOf(item, model)
    options.targetKind = if (selected != null) RobotRunTargetKind.SELECTION else RobotRunTargetKind.PATHS
    options.targetPaths = mutableListOf()
    options.selection = listOfNotNull(selected?.second).toMutableList()
    options.topLevelSuite = selected?.first
}

/**
 * What identifies the target of a configuration for gutter and context runs: its kind and, for tests and suites, the
 * kinds and full names of its items, independent of line numbers, or its paths.
 */
internal fun targetKey(
    options: RobotCodeRunConfigurationOptions
): Pair<RobotRunTargetKind, List<Pair<String?, String?>>> {
    return options.targetKind to when (options.targetKind) {
        RobotRunTargetKind.SELECTION -> options.selection.map { it.kind to it.name }
        RobotRunTargetKind.PATHS -> options.targetPaths.map { null to it }
    }
}

/**
 * Resolves the stored items of a "Tests and suites" target at the start of a run. They are passed as discovery
 * reported them, with [storedTopLevelSuite], or the top-level suite of the current discovery [model] when none is
 * stored. An item that has only a full name is looked up in the model; if the model lacks it, only its name is passed.
 */
internal fun resolveStoredSelection(
    items: List<RobotRunSelectionItem>, storedTopLevelSuite: String?, model: Array<RobotCodeTestItem>
): ResolvedSelection {
    val topLevel = storedTopLevelSuite ?: model.firstOrNull()?.children?.firstOrNull()?.longname
    val entries = items.flatMap { item ->
        val name = item.name ?: return@flatMap emptyList()
        if (item.kind != null) {
            return@flatMap listOf(SelectionEntry(name, item.suite, item.suiteRelSource ?: item.relSource))
        }
        val found = model.asSequence().flatMap { it.withDescendants() }.firstOrNull { it.longname == name }
        if (found != null) resolveSelection(listOf(found), model).entries else listOf(SelectionEntry(name, null, null))
    }
    return ResolvedSelection(topLevel, entries)
}

/**
 * The arguments for Robot Framework that a stored target passes: the paths for files and folders, each through
 * [expandPath], and the selection arguments for tests and suites. Without arguments, robotcode runs the paths of
 * `robot.toml` or the project folder.
 */
internal fun targetArguments(
    options: RobotCodeRunConfigurationOptions,
    model: Array<RobotCodeTestItem>,
    supportsParseInclude: Boolean,
    expandPath: (String) -> String = { it }
): List<String> {
    return when (options.targetKind) {
        RobotRunTargetKind.PATHS -> options.targetPaths.filter { it.isNotBlank() }.map(expandPath)
        RobotRunTargetKind.SELECTION -> selectionArguments(
            resolveStoredSelection(options.selection, options.topLevelSuite, model), supportsParseInclude
        )
    }
}

/**
 * The arguments for Robot Framework that select [selection], in the order of VS Code's Test Explorer: `-I` for each
 * file or folder, only when Robot Framework supports `--parseinclude`, `-N` with the top-level suite, `-s` for each
 * suite and `-bl` for each item. No arguments mean a run of the whole project.
 */
internal fun selectionArguments(selection: ResolvedSelection, supportsParseInclude: Boolean): List<String> {
    if (selection.entries.isEmpty()) {
        return emptyList()
    }
    return buildList {
        if (supportsParseInclude) {
            selection.entries.mapNotNull { it.relSource }.distinct()
                .forEach { addAll(listOf("-I", escapeRobotGlob(it))) }
        }
        selection.topLevelSuite?.let { addAll(listOf("-N", it)) }
        selection.entries.mapNotNull { it.suite }.distinct().forEach { addAll(listOf("-s", escapeRobotGlob(it))) }
        selection.entries.forEach { addAll(listOf("-bl", it.longname)) }
    }
}
