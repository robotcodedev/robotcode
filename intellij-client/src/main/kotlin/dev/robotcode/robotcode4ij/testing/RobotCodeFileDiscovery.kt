package dev.robotcode.robotcode4ij.testing

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.openapi.project.Project
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import dev.robotcode.robotcode4ij.defaultPathArguments
import dev.robotcode.robotcode4ij.discoveryRobotArguments
import dev.robotcode.robotcode4ij.robotSettings
import dev.robotcode.robotcode4ij.rootPythonPath
import dev.robotcode.robotcode4ij.utils.escapeRobotGlob

/**
 * The command line of the full discovery of the project.
 */
internal fun Project.fullDiscoveryCommandLine(): GeneralCommandLine {
    val arguments = fullDiscoveryArguments(robotSettings, rootPythonPath())
    return buildRobotCodeCommandLine(arguments.toTypedArray(), format = "json")
        .withCharset(Charsets.UTF_8).withWorkDirectory(basePath)
}

/**
 * The arguments of the full discovery: the default paths of the settings of the "Robot" page before `discover`, and
 * their other discovery arguments after it, with the [roots] that the switches of the page add.
 */
internal fun fullDiscoveryArguments(
    settings: RobotCodeProjectConfiguration.ProjectState, roots: List<String> = emptyList()
): List<String> {
    return defaultPathArguments(settings.robotPaths) + listOf("discover", "--read-from-stdin", "all") +
        discoveryRobotArguments(settings, roots)
}

/**
 * The arguments of the discovery of a single suite file. `discover all` returns tests and tasks alike, so the same call
 * works for test suites, task suites and projects with `rpa = true`; `-I` is passed only with parse-include support.
 * `-N` sets the [topLevelSuite] name of the last full discovery, as the runs do: with several test paths, Robot
 * Framework names the top-level suite after the suites it keeps, and the file's suite would get another ID (RF #4289).
 * The settings of the "Robot" page come as in the full discovery, before the selection of the file, as in VS Code.
 */
internal fun fileDiscoveryArguments(
    longname: String, relSource: String?, supportsParseInclude: Boolean,
    settings: RobotCodeProjectConfiguration.ProjectState, roots: List<String> = emptyList(),
    topLevelSuite: String? = null
): Array<String> {
    return buildList {
        addAll(fullDiscoveryArguments(settings, roots))
        if (supportsParseInclude && relSource != null) {
            addAll(listOf("-I", escapeRobotGlob(relSource)))
        }
        if (topLevelSuite != null) {
            addAll(listOf("-N", topLevelSuite))
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

/**
 * A copy of [items] in which the item with [suiteId] has [children]. Only the items on the path to it are copied, so the
 * old tree stays as it was and the other items are shared. Null when the tree has no item with [suiteId].
 */
internal fun replaceSuiteChildren(
    items: Array<RobotCodeTestItem>,
    suiteId: String,
    children: Array<RobotCodeTestItem>
): Array<RobotCodeTestItem>? {
    items.forEachIndexed { index, item ->
        val replaced = if (item.id == suiteId) {
            item.copy(children = children)
        } else {
            item.children?.let { replaceSuiteChildren(it, suiteId, children) }?.let { item.copy(children = it) }
        }
        if (replaced != null) {
            return items.copyOf().also { it[index] = replaced }
        }
    }
    return null
}
