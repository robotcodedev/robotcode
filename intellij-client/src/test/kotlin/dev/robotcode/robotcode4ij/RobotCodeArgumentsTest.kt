package dev.robotcode.robotcode4ij

import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeArgumentsTest {

    private fun arguments(
        extraArgs: List<String> = emptyList(),
        format: String = "",
        noColor: Boolean = true,
        noPager: Boolean = true,
        profiles: List<String> = emptyList(),
        args: List<String> = emptyList()
    ) = robotCodeArguments(extraArgs, format, noColor, noPager, profiles, args)

    @Test
    fun argumentOrder() {
        val cases = listOf(
            arguments(
                extraArgs = listOf("--log", "--log-level", "INFO"),
                format = "json",
                args = listOf("discover", "all")
            ) to listOf("--log", "--log-level", "INFO", "--format", "json", "--no-color", "--no-pager", "discover", "all"),
            // click keeps the last --format, so discovery still reads json
            arguments(extraArgs = listOf("--format", "toml"), format = "json", args = listOf("discover", "all"))
                to listOf("--format", "toml", "--format", "json", "--no-color", "--no-pager", "discover", "all"),
            arguments(profiles = listOf("dev", "ci"), args = listOf("discover", "all"))
                to listOf("--no-color", "--no-pager", "-p", "dev", "-p", "ci", "discover", "all"),
            arguments(extraArgs = listOf("--log"), args = listOf("language-server", "--socket", "1234"))
                to listOf("--log", "--no-color", "--no-pager", "language-server", "--socket", "1234"),
            arguments(noColor = false, noPager = false) to emptyList()
        )
        for ((actual, expected) in cases) {
            assertEquals(expected, actual)
        }
    }
}
