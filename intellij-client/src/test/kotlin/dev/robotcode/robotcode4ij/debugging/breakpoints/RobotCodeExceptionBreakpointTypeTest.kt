package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.util.xmlb.XmlSerializer
import dev.robotcode.robotcode4ij.debugging.FAILED_TEST_FILTER
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeFailureKind.FAILED_KEYWORDS
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeFailureKind.FAILED_SUITES
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeFailureKind.FAILED_TESTS
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeFailureKind.UNCAUGHT_FAILED_KEYWORDS

class RobotCodeExceptionBreakpointTypeTest : BasePlatformTestCase() {

    // stores the properties as the project does and loads them into new ones
    private fun storedAndLoaded(properties: RobotCodeExceptionBreakpointProperties): RobotCodeExceptionBreakpointProperties {
        val element = XmlSerializer.serialize(properties.state)
        val stored = XmlSerializer.deserialize(element, RobotCodeExceptionBreakpointProperties::class.java)
        return RobotCodeExceptionBreakpointProperties().apply { loadState(stored) }
    }

    fun testAKindIsKept() {
        val loaded = storedAndLoaded(RobotCodeExceptionBreakpointProperties().apply { kind = FAILED_TEST_FILTER })

        assertEquals(FAILED_TEST_FILTER, loaded.kind)
        assertEquals(FAILED_TESTS, RobotCodeFailureKind.of(loaded))
    }

    fun testTheBreakpointOfEarlierVersionsStopsAtUncaughtKeywordFailures() {
        val loaded = storedAndLoaded(RobotCodeExceptionBreakpointProperties())

        assertNull(loaded.kind)
        assertEquals(UNCAUGHT_FAILED_KEYWORDS, RobotCodeFailureKind.of(loaded))
        assertEquals(UNCAUGHT_FAILED_KEYWORDS, RobotCodeFailureKind.of(null))
    }

    fun testOnlyAStoredKindThatThisVersionDoesNotKnowIsUnknown() {
        fun stored(kind: String?) = RobotCodeExceptionBreakpointProperties().apply { this.kind = kind }

        assertTrue(RobotCodeFailureKind.isUnknown(stored("failed_flaky_keyword")))
        assertFalse(RobotCodeFailureKind.isUnknown(stored(FAILED_TEST_FILTER)))
        assertFalse(RobotCodeFailureKind.isUnknown(stored(null)))
        assertFalse(RobotCodeFailureKind.isUnknown(null))
    }

    fun testTheKindsAreNamedAsInTheBreakpointsDialog() {
        assertEquals(
            listOf("Uncaught Failed Keywords", "Failed Keywords", "Failed Tests", "Failed Suites"),
            RobotCodeFailureKind.entries.map { it.displayName }
        )
    }

    fun testTheAddButtonOffersTheKindsThatAreMissing() {
        assertEquals(listOf(FAILED_KEYWORDS, FAILED_TESTS, FAILED_SUITES), missingKinds(listOf()))
        assertEquals(listOf(FAILED_KEYWORDS, FAILED_TESTS, FAILED_SUITES), missingKinds(listOf(UNCAUGHT_FAILED_KEYWORDS)))
        assertEquals(listOf(FAILED_KEYWORDS, FAILED_SUITES), missingKinds(listOf(UNCAUGHT_FAILED_KEYWORDS, FAILED_TESTS)))
        assertEquals(listOf<RobotCodeFailureKind>(), missingKinds(RobotCodeFailureKind.entries))
    }
}
