package dev.robotcode.robotcode4ij.execution

// the basic ANSI colors of the log levels, which the console shows in the colors of the IDE's color scheme
private val LEVEL_COLORS = mapOf(
    "WARN" to "\u001b[33m",
    "ERROR" to "\u001b[31m",
    "FAIL" to "\u001b[31m",
    "DEBUG" to "\u001b[90m",
    "TRACE" to "\u001b[90m",
)

private const val RESET = "\u001b[0m"

// the level of a log message, `[ <LEVEL> ]`, after the message's time when the debugger sends timestamps
private val LEVEL = Regex("""^(?:\d{2}:\d{2}:\d{2}\.\d+ )?\[ ([A-Z]+) ] """)

/**
 * A log message that the debugger sent as [output], as the results tree shows it: colored by its level, unless the
 * debugger colored it itself, and ending with the file and line it was logged from, `(<source>:<line>)`, when the
 * debugger names them, which the console's filter links.
 */
internal fun logLine(output: String, source: String?, line: Int?): String {
    val text = output.removeSuffix("\n")
    val lineBreak = output.substring(text.length)
    val located = if (source != null && line != null && line > 0) "$text ($source:$line)" else text
    val color = LEVEL.find(text)?.groupValues?.get(1)?.let(LEVEL_COLORS::get)
    if (color == null || text.contains('\u001b')) return located + lineBreak
    // each line on its own, so that a message of several lines keeps its color on every line
    return located.lines().joinToString("\n") { if (it.isEmpty()) it else "$color$it$RESET" } + lineBreak
}
