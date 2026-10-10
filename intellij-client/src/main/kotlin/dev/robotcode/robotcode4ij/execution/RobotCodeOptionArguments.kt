package dev.robotcode.robotcode4ij.execution

import com.intellij.util.execution.ParametersListUtil
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem

/** Splits robot arguments like a command line, for runs without macro expansion. */
private val splitArguments: (String) -> List<String> = { ParametersListUtil.parse(it) }

/**
 * The arguments for Robot Framework that the options of a configuration pass, in the order of VS Code's launcher:
 * languages, mode, dry run, output directory, Python path, variable files, variables, include tags and exclude tags,
 * then the robot arguments. Unset values and blank entries pass nothing. The output directory, the Python path and the
 * variable files go through [expandPath], and [parseArguments] expands and splits the robot arguments.
 */
internal fun optionArguments(
    options: RobotCodeRunConfigurationOptions,
    expandPath: (String) -> String = { it },
    parseArguments: (String) -> List<String> = splitArguments
): List<String> {
    fun List<String>.entries() = map { it.trim() }.filter { it.isNotEmpty() }

    return buildList {
        options.languages.entries().forEach { addAll(listOf("--language", it)) }
        when (options.mode) {
            RobotRunMode.RPA -> add("--rpa")
            RobotRunMode.NORPA -> add("--norpa")
            RobotRunMode.INHERIT -> {}
        }
        if (options.dryRun) {
            add("--dryrun")
        }
        options.outputDir?.takeIf { it.isNotBlank() }?.let { addAll(listOf("-d", expandPath(it))) }
        options.pythonPath.entries().forEach { addAll(listOf("-P", expandPath(it))) }
        options.variableFiles.entries().forEach { addAll(listOf("-V", expandPath(it))) }
        options.variables.filterKeys { it.isNotBlank() }.forEach { (name, value) ->
            addAll(listOf("-v", "$name:$value"))
        }
        options.includeTags.entries().forEach { addAll(listOf("-i", it)) }
        options.excludeTags.entries().forEach { addAll(listOf("-e", it)) }
        options.robotArguments?.takeIf { it.isNotBlank() }?.let { addAll(parseArguments(it)) }
    }
}

/**
 * The arguments for Robot Framework of a run: the options of the configuration, then the arguments of its target, which
 * are the selection arguments or the paths. Paths go through [expandPath], the robot arguments through
 * [parseArguments].
 */
internal fun robotFrameworkArguments(
    options: RobotCodeRunConfigurationOptions,
    model: Array<RobotCodeTestItem>,
    supportsParseInclude: Boolean,
    expandPath: (String) -> String = { it },
    parseArguments: (String) -> List<String> = splitArguments
): List<String> {
    return optionArguments(options, expandPath, parseArguments) +
        targetArguments(options, model, supportsParseInclude, expandPath)
}
