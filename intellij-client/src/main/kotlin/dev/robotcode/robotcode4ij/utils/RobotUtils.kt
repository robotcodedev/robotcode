package dev.robotcode.robotcode4ij.utils

fun escapeRobotGlob(input: String): String {
    val globRegex = Regex("([*?\\[\\]])")
    return globRegex.replace(input) { matchResult ->
        "[" + matchResult.value + "]"
    }
}
