package dev.robotcode.robotcode4ij.debugging

import org.eclipse.lsp4j.debug.ExceptionFilterOptions
import org.eclipse.lsp4j.debug.SetExceptionBreakpointsArguments

// the exception filters of the RobotCode debugger
internal const val UNCAUGHT_FAILED_KEYWORD_FILTER = "uncaught_failed_keyword"
internal const val FAILED_KEYWORD_FILTER = "failed_keyword"
internal const val FAILED_TEST_FILTER = "failed_test"
internal const val FAILED_SUITE_FILTER = "failed_suite"

/**
 * The exception breakpoints of a debug session, each for one exception filter of the debugger: the request that the
 * debugger receives, and the breakpoint that a stop at a failure belongs to.
 */
internal class RobotCodeExceptionBreakpoints<B : Any>(private val filterOf: (B) -> String) {
    private val registered = LinkedHashSet<B>()

    fun register(breakpoint: B) {
        registered.add(breakpoint)
    }

    fun unregister(breakpoint: B) {
        registered.remove(breakpoint)
    }

    /**
     * The request for the registered breakpoints, an empty list when none is registered. The debugger reads only the
     * filter options; plain filters stay empty.
     */
    fun arguments() = SetExceptionBreakpointsArguments().apply {
        filters = arrayOf()
        filterOptions = registered.map { ExceptionFilterOptions().apply { filterId = filterOf(it) } }.toTypedArray()
    }

    /**
     * The registered breakpoint that a stop with [description] belongs to, if any. The debugger does not say which
     * keyword filter matched, so a keyword failure belongs to "Failed Keywords" when that one is registered.
     */
    fun breakpointFor(description: String?): B? {
        val filters = when (description) {
            "Keyword failed." -> listOf(FAILED_KEYWORD_FILTER, UNCAUGHT_FAILED_KEYWORD_FILTER)
            "Test failed." -> listOf(FAILED_TEST_FILTER)
            "Suite failed." -> listOf(FAILED_SUITE_FILTER)
            else -> listOf()
        }
        return filters.firstNotNullOfOrNull { filter -> registered.firstOrNull { filterOf(it) == filter } }
    }
}
