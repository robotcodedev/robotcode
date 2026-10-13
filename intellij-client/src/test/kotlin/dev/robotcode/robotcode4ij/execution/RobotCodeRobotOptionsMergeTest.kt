package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeRobotOptionsMergeTest {

    private fun project(block: RobotCodeProjectConfiguration.ProjectState.() -> Unit) =
        RobotCodeProjectConfiguration.ProjectState().apply(block)

    private fun configuration(block: RobotCodeRunConfigurationOptions.() -> Unit) =
        RobotCodeRunConfigurationOptions().apply(block)

    @Test
    fun listsOfTheRobotPageComeFirst() {
        val merged = mergeRobotOptions(
            project {
                robotPythonPath = mutableListOf("libs")
                robotVariableFiles = mutableListOf("common.py")
                robotArgs = "--loglevel DEBUG"
            },
            configuration {
                pythonPath = mutableListOf("more_libs")
                variableFiles = mutableListOf("local.py")
                robotArguments = "--name \"My Suite\""
            }
        )

        assertEquals(listOf("libs", "more_libs"), merged.pythonPath)
        assertEquals(listOf("common.py", "local.py"), merged.variableFiles)
        assertEquals(
            listOf("-P", "libs", "-P", "more_libs", "-V", "common.py", "-V", "local.py") +
                listOf("--loglevel", "DEBUG", "--name", "My Suite"),
            optionArguments(merged)
        )
    }

    @Test
    fun aVariableOfTheConfigurationWins() {
        val merged = mergeRobotOptions(
            project { robotVariables = linkedMapOf("NAME" to "1", "OTHER" to "x") },
            configuration { variables = linkedMapOf("NAME" to "2", "MORE" to "y") }
        )

        assertEquals(listOf("-v", "NAME:2", "-v", "OTHER:x", "-v", "MORE:y"), optionArguments(merged))
    }

    @Test
    fun inheritTakesTheModeOfTheRobotPage() {
        val cases = listOf(
            Triple("default", RobotRunMode.INHERIT, RobotRunMode.INHERIT),
            Triple("rpa", RobotRunMode.INHERIT, RobotRunMode.RPA),
            Triple("norpa", RobotRunMode.INHERIT, RobotRunMode.NORPA),
            Triple("rpa", RobotRunMode.NORPA, RobotRunMode.NORPA),
            Triple("norpa", RobotRunMode.RPA, RobotRunMode.RPA)
        )

        for ((pageMode, ownMode, expected) in cases) {
            val merged = mergeRobotOptions(project { robotMode = pageMode }, configuration { mode = ownMode })
            assertEquals("$pageMode / $ownMode", expected, merged.mode)
        }
    }

    @Test
    fun outputDirectoryAndLanguagesOfTheConfigurationOnlyWhenSet() {
        val page = project {
            robotOutputDir = "results/ide"
            robotLanguages = mutableListOf("de")
        }

        val fromPage = mergeRobotOptions(page, configuration { languages = mutableListOf(" ") })
        val own = mergeRobotOptions(page, configuration {
            outputDir = "out2"
            languages = mutableListOf("fi")
        })

        assertEquals("results/ide", fromPage.outputDir)
        assertEquals(listOf("de"), fromPage.languages)
        assertEquals("out2", own.outputDir)
        assertEquals(listOf("fi"), own.languages)
    }

    @Test
    fun tagsDryRunAndTargetStayTheConfigurations() {
        val merged = mergeRobotOptions(
            project { robotArgs = "--loglevel DEBUG" },
            configuration {
                includeTags = mutableListOf("smoke")
                excludeTags = mutableListOf("wip")
                dryRun = true
                targetPaths = mutableListOf("examples")
            }
        )

        assertEquals(listOf("smoke"), merged.includeTags)
        assertEquals(listOf("wip"), merged.excludeTags)
        assertTrue(merged.dryRun)
        assertEquals(listOf("examples"), merged.targetPaths)
    }

    @Test
    fun mergingLeavesBothInputsUnchanged() {
        val page = project {
            robotPythonPath = mutableListOf("libs")
            robotVariables = linkedMapOf("NAME" to "1")
            robotMode = "rpa"
        }
        val own = configuration {
            pythonPath = mutableListOf("more_libs")
            variables = linkedMapOf("NAME" to "2")
        }

        mergeRobotOptions(page, own)

        assertEquals(listOf("libs"), page.robotPythonPath)
        assertEquals(mapOf("NAME" to "1"), page.robotVariables)
        assertEquals(listOf("more_libs"), own.pythonPath)
        assertEquals(mapOf("NAME" to "2"), own.variables)
        assertEquals(RobotRunMode.INHERIT, own.mode)
    }
}
