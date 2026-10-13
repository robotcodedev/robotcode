package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.process.NopProcessHandler
import com.jetbrains.rd.util.lifetime.LifetimeStatus
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.joinAll
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Collections

class RobotCodeRunScopeTest {

    @Test
    fun theScopeAndTheLifetimeEndWithTheProcess() {
        val run = RobotCodeRunScope()
        val handler = NopProcessHandler()
        handler.addProcessListener(run)
        handler.startNotify()
        assertTrue(run.scope.isActive)

        handler.destroyProcess()
        handler.waitFor(5000)

        assertFalse(run.scope.isActive)
        assertEquals(LifetimeStatus.Terminated, run.lifetime.status)
    }

    // each block finishes before the next one starts, also when it waits in between
    @Test
    fun queuedWorkRunsInTheOrderItWasQueued() = runBlocking {
        val run = RobotCodeRunScope()
        val order = Collections.synchronizedList(mutableListOf<Int>())

        listOf(60L, 20L, 0L).mapIndexed { index, wait ->
            run.queue {
                order.add(index)
                delay(wait)
                order.add(index)
            }
        }.joinAll()

        assertEquals(listOf(0, 0, 1, 1, 2, 2), order)
        run.scope.cancel()
    }

    @Test
    fun aFailureDoesNotStopTheWorkQueuedAfterIt() = runBlocking {
        val run = RobotCodeRunScope()
        val done = mutableListOf<String>()

        listOf(
            run.queue { error("the debugger refused") },
            run.queue { done.add("second") },
        ).joinAll()

        assertEquals(listOf("second"), done)
        run.scope.cancel()
    }
}
