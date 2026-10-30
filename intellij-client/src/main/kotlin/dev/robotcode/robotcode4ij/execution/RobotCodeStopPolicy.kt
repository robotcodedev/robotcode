package dev.robotcode.robotcode4ij.execution

import java.util.concurrent.CompletableFuture
import java.util.concurrent.atomic.AtomicBoolean

/**
 * How a Robot Framework run is stopped: the RobotCode debugger is asked to end the run, which Robot Framework then does
 * as on Ctrl+C in a terminal. The process is interrupted as before only when there is no connection to the debugger,
 * the request cannot be sent, or the debugger does not confirm it within [timeoutMillis].
 */
internal class RobotCodeStopPolicy(
    // sends `terminate` and returns its response, or null without a connection to the debugger
    private val terminate: () -> CompletableFuture<*>?,
    private val fallback: () -> Unit,
    private val schedule: (delayMillis: Long, task: () -> Unit) -> Unit,
    private val timeoutMillis: Long = DEFAULT_TIMEOUT_MILLIS,
) {
    companion object {
        const val DEFAULT_TIMEOUT_MILLIS = 5000L
    }

    private val requested = AtomicBoolean(false)
    private val confirmed = AtomicBoolean(false)
    private val fellBack = AtomicBoolean(false)

    /** Completes once a stop has settled: the debugger confirmed `terminate`, or the process was interrupted instead. */
    val settled = CompletableFuture<Unit>()

    /** Stops the run; a second call sends no second `terminate`, which the debugger would answer with SIGTERM. */
    fun stop() {
        if (!requested.compareAndSet(false, true)) return
        val response = try {
            terminate()
        } catch (_: Exception) {
            null
        }
        if (response == null) {
            fallBack()
            return
        }
        response.whenComplete { _, error ->
            if (error == null) {
                confirmed.set(true)
                settled.complete(Unit)
            } else {
                fallBack()
            }
        }
        schedule(timeoutMillis) { if (!confirmed.get()) fallBack() }
    }

    private fun fallBack() {
        if (fellBack.compareAndSet(false, true)) {
            try {
                fallback()
            } finally {
                settled.complete(Unit)
            }
        }
    }
}
