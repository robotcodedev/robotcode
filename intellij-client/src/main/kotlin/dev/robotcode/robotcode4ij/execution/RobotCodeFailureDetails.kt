package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.debugging.RobotExecutionAttributes

// the line above a failure that the test caught before, which Robot Framework's log keeps collapsed
private const val CAUGHT = "Caught"

/**
 * The stack trace of a test that failed in the keywords [failedKeywords], which the listener reports newest first:
 * one line per keyword, innermost first, with the keyword's library or resource and the file and line of its call;
 * then the keywords whose failure was caught, each failure under a line with its message. Null for a test that did not
 * fail in a keyword.
 */
internal fun failureStackTrace(failedKeywords: Array<RobotExecutionAttributes>?): String? {
    if (failedKeywords.isNullOrEmpty()) return null
    val (caught, failure) = failedKeywords.reversed().partition { it.caught == true }
    val lines = failure.map(::stackTraceLine).toMutableList()
    caught.forEachIndexed { index, keyword ->
        // the keywords of one caught failure share its message
        if (index == 0 || keyword.message != caught[index - 1].message) lines.add(caughtLine(keyword.message))
        lines.add(stackTraceLine(keyword))
    }
    return lines.joinToString("\n")
}

private fun caughtLine(message: String?): String {
    val first = message?.lineSequence()?.first()?.takeIf { it.isNotBlank() }
    return if (first == null) CAUGHT else "$CAUGHT: $first"
}

private fun stackTraceLine(keyword: RobotExecutionAttributes): String {
    val name = listOfNotNull(keyword.libname?.takeIf { it.isNotEmpty() }, keyword.kwname).joinToString(".")
    val line = keyword.lineno?.let { ":$it" } ?: ""
    return "    at $name (${keyword.source}$line)"
}

/** The lines of a [stackTrace] before its first caught failure, the only ones that navigating from the test uses. */
internal fun failurePathOf(stackTrace: String): String =
    stackTrace.lineSequence().takeWhile { it != CAUGHT && !it.startsWith("$CAUGHT: ") }.joinToString("\n")

/**
 * The number of tests and tasks among the [items] that the listener sends with `robotEnqueued` when the run starts:
 * suites as `<source>;<long name>`, tests and tasks as `<source>;<long name>;<line>`. Tests that Robot Framework left
 * out of the run are not among them.
 */
internal fun enqueuedTestCount(items: Array<String>?): Int =
    items?.count { item -> item.split(';').let { it.size >= 3 && it.last().toIntOrNull() != null } } ?: 0
