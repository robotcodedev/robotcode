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
