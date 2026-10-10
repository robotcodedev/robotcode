package dev.robotcode.robotcode4ij.execution

import com.intellij.util.execution.ParametersListUtil
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeOptionArgumentsTest {

    private fun options(setup: RobotCodeRunConfigurationOptions.() -> Unit) =
        RobotCodeRunConfigurationOptions().apply(setup)

    @Test
    fun eachOptionPassesItsRobotFrameworkOption() {
        val table = listOf(
            options { languages = mutableListOf("de", "fi") } to listOf("--language", "de", "--language", "fi"),
            options { mode = RobotRunMode.RPA } to listOf("--rpa"),
            options { mode = RobotRunMode.NORPA } to listOf("--norpa"),
            options { mode = RobotRunMode.INHERIT } to listOf(),
            options { dryRun = true } to listOf("--dryrun"),
            options { outputDir = "out2" } to listOf("-d", "out2"),
            options { pythonPath = mutableListOf("lib", "resources") } to listOf("-P", "lib", "-P", "resources"),
            options { variableFiles = mutableListOf("vars.py") } to listOf("-V", "vars.py"),
            options { variables = linkedMapOf("NAME" to "x") } to listOf("-v", "NAME:x"),
            options { includeTags = mutableListOf("smoke", "my tag") } to listOf("-i", "smoke", "-i", "my tag"),
            options { excludeTags = mutableListOf("slow") } to listOf("-e", "slow"),
            options { robotArguments = "--loglevel DEBUG" } to listOf("--loglevel", "DEBUG"),
        )
        for ((options, expected) in table) {
            assertEquals(expected, optionArguments(options))
        }
    }

    @Test
    fun allOptionsFollowTheOrderOfVsCodesLauncher() {
        val options = options {
            robotArguments = "--loglevel DEBUG"
            excludeTags = mutableListOf("slow")
            includeTags = mutableListOf("smoke")
            variables = linkedMapOf("NAME" to "x")
            variableFiles = mutableListOf("vars.py")
            pythonPath = mutableListOf("lib")
            outputDir = "out2"
            dryRun = true
            mode = RobotRunMode.RPA
            languages = mutableListOf("de")
        }

        assertEquals(
            listOf(
                "--language", "de", "--rpa", "--dryrun", "-d", "out2", "-P", "lib", "-V", "vars.py", "-v", "NAME:x",
                "-i", "smoke", "-e", "slow", "--loglevel", "DEBUG"
            ),
            optionArguments(options)
        )
    }

    @Test
    fun unsetValuesAndBlankEntriesPassNothing() {
        assertEquals(listOf<String>(), optionArguments(RobotCodeRunConfigurationOptions()))
        val blank = options {
            robotArguments = "  "
            outputDir = " "
            languages = mutableListOf("", " ")
            variables = linkedMapOf("" to "x", " " to "y")
            includeTags = mutableListOf("")
        }
        assertEquals(listOf<String>(), optionArguments(blank))
    }

    @Test
    fun valuesKeepQuotesColonsAndWindowsPaths() {
        val options = options {
            robotArguments = "--metadata \"Build:1 2\""
            variables = linkedMapOf("URL" to "http://host:8080/a b")
            variableFiles = mutableListOf("C:\\My Vars\\vars.py")
            outputDir = "C:\\Robot Out"
        }

        assertEquals(
            listOf(
                "-d", "C:\\Robot Out", "-V", "C:\\My Vars\\vars.py", "-v", "URL:http://host:8080/a b",
                "--metadata", "Build:1 2"
            ),
            optionArguments(options)
        )
    }

    // every value holds the macro $X$; paths and robot arguments get different replacements
    private fun macroOptions(kind: RobotRunTargetKind) = options {
        targetKind = kind
        targetPaths = mutableListOf("\$X\$/tests")
        selection = mutableListOf(RobotRunSelectionItem().apply { name = "Project.\$X\$" })
        outputDir = "\$X\$/out"
        pythonPath = mutableListOf("\$X\$/lib")
        variableFiles = mutableListOf("\$X\$/vars.py")
        variables = linkedMapOf("NAME" to "\$X\$")
        languages = mutableListOf("\$X\$")
        includeTags = mutableListOf("\$X\$")
        excludeTags = mutableListOf("\$X\$")
        robotArguments = "--metadata Dir:\$X\$"
    }

    private fun expandedArguments(options: RobotCodeRunConfigurationOptions) = robotFrameworkArguments(
        options, arrayOf(), supportsParseInclude = true,
        expandPath = { it.replace("\$X\$", "/path") },
        parseArguments = { ParametersListUtil.parse(it.replace("\$X\$", "/args")) }
    )

    @Test
    fun onlyPathsAndRobotArgumentsGoThroughTheMacroExpansion() {
        val options = macroOptions(RobotRunTargetKind.PATHS)

        assertEquals(
            listOf(
                "--language", "\$X\$", "-d", "/path/out", "-P", "/path/lib", "-V", "/path/vars.py", "-v", "NAME:\$X\$",
                "-i", "\$X\$", "-e", "\$X\$", "--metadata", "Dir:/args", "/path/tests"
            ),
            expandedArguments(options)
        )
        // the stored values keep their macros
        assertEquals(macroOptions(RobotRunTargetKind.PATHS), options)
    }

    @Test
    fun namesOfTestsAndSuitesKeepTheirText() {
        val options = macroOptions(RobotRunTargetKind.SELECTION)

        assertEquals(listOf("-bl", "Project.\$X\$"), expandedArguments(options).takeLast(2))
        assertEquals(macroOptions(RobotRunTargetKind.SELECTION), options)
    }
}
