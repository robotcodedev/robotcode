package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.process.NopProcessHandler
import dev.robotcode.robotcode4ij.execution.RobotCodeStopPolicy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CompletableFuture

class RobotCodePythonSessionHandlerTest {

    // the run's handler as the plugin's handler stops it: through the stop policy, whose `terminate` the test answers
    private class FakeRunHandler : NopProcessHandler() {
        var sent = 0
        val response = CompletableFuture<Void>()
        val policy = RobotCodeStopPolicy(
            terminate = { sent++; response },
            fallback = { notifyProcessTerminated(130) },
            schedule = { _, _ -> },
        )

        override fun destroyProcessImpl() {
            policy.stop()
        }

        fun end(exitCode: Int) = notifyProcessTerminated(exitCode)
    }

    private val run = FakeRunHandler().apply { startNotify() }
    private val python = RobotCodePythonSessionHandler(run, run.policy.settled).apply { startNotify() }

    @Test
    fun stoppingThePythonSessionStopsTheRunAndEndsOnlyOnceTheStopHasSettled() {
        python.destroyProcess()

        assertEquals(1, run.sent)
        assertFalse(python.waitFor(200))

        run.response.complete(null)

        assertTrue(python.waitFor(5000))
    }

    @Test
    fun stoppingTheRunEndsThePythonSessionOnlyOnceTheStopHasSettled() {
        run.destroyProcess()

        assertEquals(1, run.sent)
        assertFalse(python.waitFor(200))

        run.response.complete(null)

        assertTrue(python.waitFor(5000))
    }

    @Test
    fun thePythonSessionEndsWithTheRun() {
        run.end(0)

        assertTrue(python.waitFor(5000))
        assertEquals(0, python.exitCode)
    }

    @Test
    fun aStopFromEitherSideSendsOneTerminate() {
        python.destroyProcess()
        run.destroyProcess()
        python.destroyProcess()

        assertEquals(1, run.sent)
    }

    @Test
    fun aStopThatFallsBackEndsThePythonSession() {
        python.destroyProcess()
        run.response.completeExceptionally(IllegalStateException("connection closed"))

        assertTrue(python.waitFor(5000))
        assertTrue(run.isProcessTerminated)
    }

    @Test
    fun aPythonSessionOfARunThatHasEndedEndsAtOnce() {
        val ended = FakeRunHandler().apply { startNotify(); end(1) }
        val late = RobotCodePythonSessionHandler(ended, ended.policy.settled).apply { startNotify() }

        assertTrue(late.waitFor(5000))
        assertEquals(1, late.exitCode)
    }
}
