package dev.robotcode.robotcode4ij.execution

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException
import java.util.concurrent.CompletableFuture

class RobotCodeStopPolicyTest {

    private var sent = 0
    private var fallbacks = 0
    private val scheduled = mutableListOf<Pair<Long, () -> Unit>>()

    private fun policy(response: () -> CompletableFuture<*>?) = RobotCodeStopPolicy(
        terminate = { sent++; response() },
        fallback = { fallbacks++ },
        schedule = { delayMillis, task -> scheduled.add(delayMillis to task) },
    )

    private fun runScheduled() = scheduled.forEach { it.second() }

    @Test
    fun theDebuggerIsAskedOnceAndNothingElseHappensWhileItAnswers() {
        policy { CompletableFuture<Void>() }.stop()

        assertEquals(1, sent)
        assertEquals(0, fallbacks)
        assertEquals(listOf(5000L), scheduled.map { it.first })
    }

    @Test
    fun aConfirmedStopNeedsNoFallback() {
        val response = CompletableFuture<Void>()
        policy { response }.stop()

        response.complete(null)
        runScheduled()

        assertEquals(0, fallbacks)
    }

    @Test
    fun anUnconfirmedStopFallsBackOnceAfterTheTimeout() {
        val response = CompletableFuture<Void>()
        policy { response }.stop()

        runScheduled()
        // an answer after the timeout changes nothing
        response.complete(null)

        assertEquals(1, fallbacks)
    }

    @Test
    fun aRequestThatFailsFallsBackOnce() {
        val response = CompletableFuture<Void>()
        policy { response }.stop()

        response.completeExceptionally(IOException("connection closed"))
        runScheduled()

        assertEquals(1, fallbacks)
    }

    @Test
    fun aRequestThatCannotBeSentFallsBackAtOnce() {
        policy { throw IllegalStateException("not connected") }.stop()

        assertEquals(1, fallbacks)
        assertEquals(listOf<Long>(), scheduled.map { it.first })
    }

    @Test
    fun withoutAConnectionTheProcessIsInterruptedAtOnce() {
        policy { null }.stop()

        assertEquals(1, fallbacks)
        assertEquals(listOf<Long>(), scheduled.map { it.first })
    }

    @Test
    fun aSecondStopSendsNoSecondTerminate() {
        val stopPolicy = policy { CompletableFuture<Void>() }

        stopPolicy.stop()
        stopPolicy.stop()

        assertEquals(1, sent)
        assertEquals(0, fallbacks)
    }

    @Test
    fun aStopSettlesWhenTheDebuggerConfirmsIt() {
        val response = CompletableFuture<Void>()
        val stopPolicy = policy { response }
        assertFalse(stopPolicy.settled.isDone)

        stopPolicy.stop()
        assertFalse(stopPolicy.settled.isDone)
        response.complete(null)

        assertTrue(stopPolicy.settled.isDone)
        assertEquals(0, fallbacks)
    }

    @Test
    fun aStopSettlesWithTheFallback() {
        // after the timeout
        val unanswered = policy { CompletableFuture<Void>() }
        unanswered.stop()
        assertFalse(unanswered.settled.isDone)
        runScheduled()
        assertTrue(unanswered.settled.isDone)

        // after a failed request
        val failing = CompletableFuture<Void>()
        val failed = policy { failing }
        failed.stop()
        failing.completeExceptionally(IOException("connection closed"))
        assertTrue(failed.settled.isDone)

        // without a connection
        val unconnected = policy { null }
        unconnected.stop()
        assertTrue(unconnected.settled.isDone)
    }

    @Test
    fun aStopSettlesOnlyOnce() {
        val response = CompletableFuture<Void>()
        val stopPolicy = policy { response }
        var settlements = 0
        stopPolicy.settled.thenRun { settlements++ }

        stopPolicy.stop()
        runScheduled()
        // a late answer and a second stop change nothing
        response.complete(null)
        stopPolicy.stop()

        assertEquals(1, settlements)
        assertEquals(1, sent)
    }
}
