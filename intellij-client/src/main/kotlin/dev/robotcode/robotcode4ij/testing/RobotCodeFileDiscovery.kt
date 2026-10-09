package dev.robotcode.robotcode4ij.testing

import dev.robotcode.robotcode4ij.utils.escapeRobotGlob

/**
 * The arguments of the discovery of a single suite file. `discover all` returns tests and tasks alike, so the same call
 * works for test suites, task suites and projects with `rpa = true`; `-I` is passed only with parse-include support.
 */
internal fun fileDiscoveryArguments(longname: String, relSource: String?, supportsParseInclude: Boolean): Array<String> {
    return buildList {
        // TODO: Add support for configurable paths
        addAll(listOf("-dp", ".", "discover", "--read-from-stdin", "all"))
        if (supportsParseInclude && relSource != null) {
            addAll(listOf("-I", escapeRobotGlob(relSource)))
        }
        addAll(listOf("--suite", escapeRobotGlob(longname)))
    }.toTypedArray()
}

/**
 * The children of the item with [suiteId] in the tree that the discovery of a single file returns, or null when the tree
 * has no such item or the item has no children, for example after the last test or task of the file was deleted.
 */
internal fun findSuiteChildren(items: Array<RobotCodeTestItem>?, suiteId: String): Array<RobotCodeTestItem>? {
    items?.forEach { item ->
        if (item.id == suiteId) {
            return item.children?.takeIf { it.isNotEmpty() }
        }
        findSuiteChildren(item.children, suiteId)?.let { return it }
    }
    return null
}
