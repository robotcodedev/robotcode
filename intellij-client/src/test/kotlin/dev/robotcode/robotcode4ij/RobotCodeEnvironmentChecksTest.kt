package dev.robotcode.robotcode4ij

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Test
import java.util.Collections
import java.util.concurrent.atomic.AtomicInteger

class RobotCodeEnvironmentChecksTest {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val interpreter = PythonInterpreter(InterpreterKind.LOCAL, "Python 3.12", "/usr/bin/python3")
    private val usable = EnvironmentState.Checked(EnvironmentResult.Usable)
    private val failed = EnvironmentState.Failed("it ended with exit code 1.")

    private val probes = AtomicInteger()
    private val changes: MutableList<EnvironmentState> = Collections.synchronizedList(mutableListOf())

    @After
    fun tearDown() {
        scope.cancel()
    }

    private fun checks(probe: suspend () -> EnvironmentState) = EnvironmentChecks(scope, {
        probes.incrementAndGet()
        probe()
    }) { _, state -> changes.add(state) }

    private fun await(checks: EnvironmentChecks) = runBlocking {
        withTimeout(5_000) { checks.running(interpreter)?.await() }
    }

    @Test
    fun twoRequestsRunOneProbe() {
        val gate = CompletableDeferred<Unit>()
        val checks = checks { gate.await(); usable }

        checks.request(interpreter)
        checks.request(interpreter)
        gate.complete(Unit)
        await(checks)

        assertEquals(1, probes.get())
        assertEquals(usable, checks.state(interpreter))
    }

    @Test
    fun failedCheckIsKeptAndNotRepeatedByAnotherRequest() {
        val checks = checks { failed }

        checks.request(interpreter)
        await(checks)
        checks.request(interpreter)
        await(checks)

        assertEquals(1, probes.get())
        assertEquals(failed, checks.state(interpreter))
    }

    @Test
    fun resetStartsANewProbe() {
        val checks = checks { usable }

        checks.request(interpreter)
        await(checks)
        runBlocking { withTimeout(5_000) { checks.reset(interpreter).await() } }

        assertEquals(2, probes.get())
    }

    @Test
    fun resetDuringACheckRunsTheProbeAgainOneAfterTheOther() {
        val gate = CompletableDeferred<Unit>()
        val running = AtomicInteger()
        var parallel = 0
        val checks = checks {
            if (running.incrementAndGet() > 1) parallel++
            gate.await()
            running.decrementAndGet()
            usable
        }

        checks.request(interpreter)
        val result = checks.reset(interpreter)
        gate.complete(Unit)
        runBlocking { withTimeout(5_000) { result.await() } }

        assertEquals(2, probes.get())
        assertEquals(0, parallel)
    }

    @Test
    fun checkThatEndsWithoutAResultLeavesNoState() {
        val ownScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
        val started = CompletableDeferred<Unit>()
        val checks = EnvironmentChecks(ownScope, { started.complete(Unit); CompletableDeferred<EnvironmentState>().await() }) { _, _ -> }

        checks.request(interpreter)
        runBlocking { withTimeout(5_000) { started.await() } }
        ownScope.cancel()
        runBlocking { withTimeout(5_000) { ownScope.coroutineContext[Job]!!.join() } }

        assertEquals(EnvironmentState.Unknown, checks.state(interpreter))
        assertEquals(null, checks.running(interpreter))
    }

    @Test
    fun everyStateChangeReachesTheSubscriber() {
        val checks = checks { failed }

        checks.request(interpreter)
        await(checks)
        runBlocking { withTimeout(5_000) { checks.reset(interpreter).await() } }

        assertEquals(listOf(EnvironmentState.Checking, failed, EnvironmentState.Checking, failed), changes.toList())
    }
}
