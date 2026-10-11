package dev.robotcode.robotcode4ij.debugging

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Test

class RobotCodeExceptionBreakpointsTest {

    private class Breakpoint(val filter: String)

    private val breakpoints = RobotCodeExceptionBreakpoints<Breakpoint> { it.filter }

    private val uncaught = Breakpoint(UNCAUGHT_FAILED_KEYWORD_FILTER)
    private val keywords = Breakpoint(FAILED_KEYWORD_FILTER)
    private val tests = Breakpoint(FAILED_TEST_FILTER)
    private val suites = Breakpoint(FAILED_SUITE_FILTER)

    private fun requestedFilters() = breakpoints.arguments().filterOptions.map { it.filterId }

    @Test
    fun theRequestHasExactlyTheRegisteredFilters() {
        breakpoints.register(uncaught)
        breakpoints.register(tests)

        assertEquals(listOf(UNCAUGHT_FAILED_KEYWORD_FILTER, FAILED_TEST_FILTER), requestedFilters())
        assertEquals(0, breakpoints.arguments().filters.size)

        breakpoints.unregister(uncaught)
        breakpoints.unregister(tests)

        // an empty list, so that the debugger drops its default filter as well
        assertNotNull(breakpoints.arguments().filterOptions)
        assertEquals(listOf<String>(), requestedFilters())
    }

    @Test
    fun aStopBelongsToTheBreakpointOfItsFailure() {
        listOf(uncaught, keywords, tests, suites).forEach { breakpoints.register(it) }

        assertSame(keywords, breakpoints.breakpointFor("Keyword failed."))
        assertSame(tests, breakpoints.breakpointFor("Test failed."))
        assertSame(suites, breakpoints.breakpointFor("Suite failed."))
    }

    @Test
    fun aKeywordFailureBelongsToUncaughtFailedKeywordsWithoutFailedKeywords() {
        breakpoints.register(uncaught)

        assertSame(uncaught, breakpoints.breakpointFor("Keyword failed."))
    }

    @Test
    fun aStopWithoutARegisteredBreakpointBelongsToNone() {
        breakpoints.register(uncaught)

        assertNull(breakpoints.breakpointFor("Test failed."))
        assertNull(breakpoints.breakpointFor("Suite failed."))
        assertNull(breakpoints.breakpointFor("Paused"))
        assertNull(breakpoints.breakpointFor(null))
    }
}
