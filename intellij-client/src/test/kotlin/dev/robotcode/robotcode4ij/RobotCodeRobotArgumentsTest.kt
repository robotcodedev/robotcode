package dev.robotcode.robotcode4ij

import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeRobotArgumentsTest {

    private fun settings(block: RobotCodeProjectConfiguration.ProjectState.() -> Unit) =
        RobotCodeProjectConfiguration.ProjectState().apply(block)

    @Test
    fun defaultPathsOrTheProjectFolder() {
        val cases = listOf(
            listOf<String>() to listOf("-dp", "."),
            listOf("", " ") to listOf("-dp", "."),
            listOf("tests") to listOf("-dp", "tests"),
            listOf(" tests ", "", "examples") to listOf("-dp", "tests", "-dp", "examples")
        )

        for ((paths, expected) in cases) {
            assertEquals("$paths", expected, defaultPathArguments(paths))
        }
    }

    @Test
    fun discoveryArgumentsInTheOrderOfVsCode() {
        val cases = listOf(
            settings {} to listOf(),
            settings { robotMode = "default" } to listOf(),
            settings { robotMode = "norpa" } to listOf("--norpa"),
            settings { robotMode = "unknown" } to listOf(),
            settings {
                robotArgs = "--exclude wip"
                robotLanguages = mutableListOf("de", " ")
                robotPythonPath = mutableListOf(" libs ")
                robotMode = "rpa"
            } to listOf("--rpa", "-P", "libs", "--language", "de", "--exclude", "wip"),
            settings { robotArgs = "--name \"My Suite\"" } to listOf("--name", "My Suite")
        )

        for ((state, expected) in cases) {
            assertEquals(expected, discoveryRobotArguments(state))
        }
    }

    // discovery gets neither variables nor variable files nor the environment, as in VS Code
    @Test
    fun discoveryLeavesOutVariablesAndTheEnvironment() {
        val state = settings {
            robotVariables = linkedMapOf("NAME" to "1")
            robotVariableFiles = mutableListOf("vars.py")
            robotEnv = linkedMapOf("STAGE" to "dev")
            robotOutputDir = "results"
        }

        assertEquals(listOf<String>(), discoveryRobotArguments(state))
    }
}
