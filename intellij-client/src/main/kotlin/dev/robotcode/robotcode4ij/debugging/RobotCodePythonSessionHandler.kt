package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.process.ProcessEvent
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.process.ProcessListener
import java.io.OutputStream
import java.util.concurrent.CompletableFuture
import java.util.concurrent.atomic.AtomicBoolean

/**
 * The process handler of the Python session of a Debug run with "Attach Python". It has no process of its own and
 * stands for the run's [runHandler]: it ends with the run, and stopping it stops the run as Stop in the Robot Framework
 * session does. In both directions it ends only once the run's stop has settled ([stopSettled]) or the run's process
 * has ended, because ending the Python session lets pydevd release a thread that is paused at a Python breakpoint, and
 * that thread must not go on before Robot Framework has received the stop.
 */
class RobotCodePythonSessionHandler(
    private val runHandler: ProcessHandler,
    private val stopSettled: CompletableFuture<*>,
) : ProcessHandler() {

    private val ended = AtomicBoolean(false)

    init {
        runHandler.addProcessListener(object : ProcessListener {
            // the run is being stopped from elsewhere, for example from the Robot Framework session
            override fun processWillTerminate(event: ProcessEvent, willBeDestroyed: Boolean) {
                if (willBeDestroyed) stopSettled.whenComplete { _, _ -> end() }
            }

            override fun processTerminated(event: ProcessEvent) {
                end()
            }
        })
        if (runHandler.isProcessTerminated) end()
    }

    // the user stopped the Python session
    override fun destroyProcessImpl() {
        stopSettled.whenComplete { _, _ -> end() }
        if (runHandler.isProcessTerminated) end() else runHandler.destroyProcess()
    }

    // detaching ends only the Python session; the run goes on without it
    override fun detachProcessImpl() {
        if (ended.compareAndSet(false, true)) notifyProcessDetached()
    }

    override fun detachIsDefault(): Boolean = false

    override fun getProcessInput(): OutputStream? = null

    private fun end() {
        if (ended.compareAndSet(false, true)) notifyProcessTerminated(runHandler.exitCode ?: 0)
    }
}
