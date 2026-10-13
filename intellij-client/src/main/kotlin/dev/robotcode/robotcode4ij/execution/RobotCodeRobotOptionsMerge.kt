package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettings.RobotMode
import dev.robotcode.robotcode4ij.configuration.choiceOf

/**
 * The options of a run: the [configuration]'s options combined with the settings of the "Robot" page of the [project],
 * as VS Code combines its settings with a launch configuration. The Python path, the variable files and the robot
 * arguments of the page come first, a variable of the configuration wins over the page's of the same name, and the
 * configuration's mode, output directory and languages replace the page's when the configuration sets them. Both
 * inputs stay unchanged.
 */
internal fun mergeRobotOptions(
    project: RobotCodeProjectConfiguration.ProjectState, configuration: RobotCodeRunConfigurationOptions
): RobotCodeRunConfigurationOptions {
    fun List<String>.hasEntries() = any { it.isNotBlank() }

    return RobotCodeRunConfigurationOptions().apply {
        copyFrom(configuration)
        robotArguments = listOfNotNull(project.robotArgs, configuration.robotArguments)
            .filter { it.isNotBlank() }.joinToString(" ")
        pythonPath = (project.robotPythonPath + configuration.pythonPath).toMutableList()
        variableFiles = (project.robotVariableFiles + configuration.variableFiles).toMutableList()
        variables = LinkedHashMap(project.robotVariables).apply { putAll(configuration.variables) }
        languages = (if (configuration.languages.hasEntries()) configuration.languages else project.robotLanguages)
            .toMutableList()
        outputDir = configuration.outputDir?.takeIf { it.isNotBlank() } ?: project.robotOutputDir
        if (configuration.mode == RobotRunMode.INHERIT) {
            mode = when (choiceOf<RobotMode>(project.robotMode)) {
                RobotMode.DEFAULT -> RobotRunMode.INHERIT
                RobotMode.RPA -> RobotRunMode.RPA
                RobotMode.NORPA -> RobotRunMode.NORPA
            }
        }
    }
}
