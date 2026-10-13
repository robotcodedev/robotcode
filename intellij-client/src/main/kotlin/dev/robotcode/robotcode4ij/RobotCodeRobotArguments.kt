package dev.robotcode.robotcode4ij

import com.intellij.openapi.project.Project
import com.intellij.util.execution.ParametersListUtil
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettings.RobotMode
import dev.robotcode.robotcode4ij.configuration.choiceOf

/** The stored settings of the "Robot" page of the project. */
internal val Project.robotSettings: RobotCodeProjectConfiguration.ProjectState
    get() = RobotCodeProjectConfiguration.getInstance(this).state

/**
 * `-dp` for each of [paths], or `-dp .` without any: the default paths that test discovery, the profile list and runs
 * pass to robotcode, so that runs see the suites with the names that discovery reported.
 */
internal fun defaultPathArguments(paths: List<String>): List<String> {
    val entries = paths.map { it.trim() }.filter { it.isNotEmpty() }
    return if (entries.isEmpty()) listOf("-dp", ".") else entries.flatMap { listOf("-dp", it) }
}

/**
 * The arguments that test discovery passes after its subcommand for the settings of the "Robot" page, in the order of
 * VS Code: the mode unless it is the default, `-P` for each Python path entry, `--language` for each language, then the
 * args. Variables, variable files and the environment are not passed, as in VS Code.
 */
internal fun discoveryRobotArguments(settings: RobotCodeProjectConfiguration.ProjectState): List<String> {
    fun List<String>.entries() = map { it.trim() }.filter { it.isNotEmpty() }

    return buildList {
        when (choiceOf<RobotMode>(settings.robotMode)) {
            RobotMode.RPA -> add("--rpa")
            RobotMode.NORPA -> add("--norpa")
            RobotMode.DEFAULT -> {}
        }
        settings.robotPythonPath.entries().forEach { addAll(listOf("-P", it)) }
        settings.robotLanguages.entries().forEach { addAll(listOf("--language", it)) }
        addAll(ParametersListUtil.parse(settings.robotArgs.orEmpty()).filter { it.isNotBlank() })
    }
}
