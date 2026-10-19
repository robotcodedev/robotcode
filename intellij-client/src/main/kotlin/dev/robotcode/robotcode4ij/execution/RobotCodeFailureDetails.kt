package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.debugging.RobotExecutionAttributes
import dev.robotcode.robotcode4ij.debugging.RobotFailure

// the line above a failure that the test caught before, which Robot Framework's log keeps collapsed
private const val CAUGHT = "Caught"

// the start of the line of a call, as Python starts the lines of a traceback
private const val CALL_PREFIX = "  File \""

/**
 * The stack trace of a test that failed in the keywords [failedKeywords], which the listener groups into [failures]:
 * each failure with its calls as Python lists them, from the call in the test inward, one line per call with its file
 * and line and the keyword with its library or resource. The failures that made the test fail come first, several of
 * them after an empty line and each under a line with its message; then those the test caught before, each under a
 * line with its message. Null for a test without failures, for example one that failed in its suite setup.
 */
internal fun failureStackTrace(
    failedKeywords: Array<RobotExecutionAttributes>?,
    failures: Array<RobotFailure>?,
): String? {
    if (failedKeywords == null || failures.isNullOrEmpty()) return null
    val (caught, failed) = failures.partition { failedKeywords[it.keyword].caught == true }
    val lines = mutableListOf<String>()
    // IntelliJ prints the stack trace right below the test's failure message, so the empty line keeps the message line
    // of the first failure apart from it; a single failure needs no line with its message, that message stands above
    if (failed.size > 1) lines.add("")
    for (failure in failed) {
        if (failed.size > 1) lines.add(firstLine(failedKeywords[failure.keyword].message).orEmpty())
        lines.addAll(callLines(failure.calls.map { failedKeywords[it] }))
    }
    for (failure in caught) {
        lines.add(caughtLine(failedKeywords[failure.keyword].message))
        lines.addAll(callLines(failure.calls.map { failedKeywords[it] }))
    }
    return lines.joinToString("\n")
}

private fun firstLine(message: String?): String? = message?.lineSequence()?.first()?.takeIf { it.isNotBlank() }

private fun caughtLine(message: String?): String = firstLine(message)?.let { "$CAUGHT: $it" } ?: CAUGHT

// the calls of a failure, given innermost first, from the outside in; a call on the line of the call it ran in, as a
// keyword that a Run Keyword variant runs, is left out, so that the list does not show the same code twice
private fun callLines(calls: List<RobotExecutionAttributes>): List<String> =
    calls.filterIndexed { index, call ->
        val outer = calls.getOrNull(index + 1)
        outer == null || call.source != outer.source || call.lineno != outer.lineno
    }.asReversed().map(::stackTraceLine)

private fun stackTraceLine(keyword: RobotExecutionAttributes): String {
    val name = listOfNotNull(keyword.libname?.takeIf { it.isNotEmpty() }, keyword.kwname).joinToString(".")
    val line = keyword.lineno?.let { ", line $it" } ?: ""
    return "$CALL_PREFIX${keyword.source}\"$line, in $name"
}

/**
 * The calls in a [stackTrace] before its first caught failure, the only lines that navigating from the test uses; a
 * location at the end of a failure's message is no place to navigate to.
 */
internal fun failurePathOf(stackTrace: String): String = stackTrace.lineSequence()
    .takeWhile { it != CAUGHT && !it.startsWith("$CAUGHT: ") }
    .filter { it.startsWith(CALL_PREFIX) }
    .joinToString("\n")

/**
 * The number of tests and tasks among the [items] that the listener sends with `robotEnqueued` when the run starts:
 * suites as `<source>;<long name>`, tests and tasks as `<source>;<long name>;<line>`. Tests that Robot Framework left
 * out of the run are not among them.
 */
internal fun enqueuedTestCount(items: Array<String>?): Int =
    items?.count { item -> item.split(';').let { it.size >= 3 && it.last().toIntOrNull() != null } } ?: 0
