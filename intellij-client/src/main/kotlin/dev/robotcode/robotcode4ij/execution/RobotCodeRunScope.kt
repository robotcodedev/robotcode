package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.process.ProcessEvent
import com.intellij.execution.process.ProcessListener
import com.intellij.openapi.diagnostic.logger
import com.jetbrains.rd.util.lifetime.Lifetime
import com.jetbrains.rd.util.lifetime.LifetimeDefinition
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

private val LOG = logger<RobotCodeRunScope>()

/**
 * The coroutines of one run: the connection to its debugger and the requests to it. They end, and so do the
 * subscriptions bound to [lifetime], when the process ends or is detached.
 */
class RobotCodeRunScope : ProcessListener {
    // a failure that a coroutine does not handle is logged, so that it never shows as an IDE error
    val scope = CoroutineScope(
        SupervisorJob() + Dispatchers.IO + CoroutineExceptionHandler { _, e ->
            LOG.warn("A request to the RobotCode debugger failed", e)
        }
    )

    private val lifetimeDefinition = LifetimeDefinition()

    val lifetime: Lifetime
        get() = lifetimeDefinition

    private val serial = Dispatchers.IO.limitedParallelism(1)

    private val queueMutex = Mutex()

    /**
     * Runs [block] once every block queued before it has finished, so that requests that change the run's state reach
     * the debugger in the order of the user's actions. A failure is logged and does not stop the blocks queued after
     * it.
     */
    fun queue(block: suspend () -> Unit): Job = scope.launch(serial) {
        queueMutex.withLock {
            try {
                block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                LOG.warn("A request to the RobotCode debugger failed", e)
            }
        }
    }

    override fun processTerminated(event: ProcessEvent) {
        scope.cancel()
        lifetimeDefinition.terminate()
    }
}
