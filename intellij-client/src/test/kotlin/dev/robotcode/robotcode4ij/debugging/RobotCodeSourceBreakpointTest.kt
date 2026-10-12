package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.breakpoints.SuspendPolicy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeSourceBreakpointTest {

    @Test
    fun aBreakpointWithoutOptionsSendsOnlyItsLine() {
        for (policy in SuspendPolicy.entries) {
            val sent = sourceBreakpoint(4, null, null, null, policy)

            assertEquals(5, sent.line)
            assertNull(sent.condition)
            assertNull(sent.hitCondition)
            assertNull(sent.logMessage)
        }
    }

    @Test
    fun theConditionAndTheHitCountAreSentForEveryPolicy() {
        for (policy in SuspendPolicy.entries) {
            val sent = sourceBreakpoint(4, "\${i} == 3", null, " >= 2 ", policy)

            assertEquals("\${i} == 3", sent.condition)
            assertEquals(">= 2", sent.hitCondition)
        }
    }

    @Test
    fun theLogTextIsSentOnlyForABreakpointThatDoesNotSuspend() {
        assertEquals("value is \${i}", sourceBreakpoint(4, null, "value is \${i}", null, SuspendPolicy.NONE).logMessage)
        assertNull(sourceBreakpoint(4, null, "value is \${i}", null, SuspendPolicy.ALL).logMessage)
        assertNull(sourceBreakpoint(4, null, "value is \${i}", null, SuspendPolicy.THREAD).logMessage)
    }

    @Test
    fun blankTextsAreNotSent() {
        val sent = sourceBreakpoint(4, " ", "  ", " ", SuspendPolicy.NONE)

        assertNull(sent.condition)
        assertNull(sent.hitCondition)
        assertNull(sent.logMessage)
    }
}
