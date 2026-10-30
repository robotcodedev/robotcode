package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.process.KillableColoredProcessHandler
import com.intellij.execution.process.ProcessOutputTypes
import com.intellij.openapi.util.Key
import com.intellij.util.concurrency.AppExecutorUtil
import com.intellij.util.io.BaseDataReader
import com.intellij.util.io.BaseOutputReader
import java.io.Reader
import java.nio.charset.Charset
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.Future
import java.util.concurrent.TimeUnit
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/**
 * The read cycles of an output reader: a cycle starts when the reader begins to read and completes when it has
 * delivered everything it could read and is about to sleep.
 */
internal interface ReadCycles {
    val started: Long
    val completed: Long

    // the reader reads no more, for example because the process has ended
    val stopped: Boolean

    /** Ends the reader's sleep, so that its next cycle starts at once. */
    fun wake()
}

/**
 * Waits until the output readers of a process have delivered everything the process wrote before the call: each reader
 * completes a read cycle that started after the call. The wait ends after [timeoutMillis] at the latest, and at once
 * when the process has ended.
 */
internal class OutputFence(private val timeoutMillis: Long = 500, private val terminated: () -> Boolean) {
    private val lock = ReentrantLock()
    private val cycleCompleted = lock.newCondition()
    private val readers = CopyOnWriteArrayList<ReadCycles>()

    fun add(reader: ReadCycles) {
        readers.add(reader)
    }

    // called by a reader after each completed cycle
    fun onCycleCompleted() {
        lock.withLock { cycleCompleted.signalAll() }
    }

    fun await() {
        if (terminated()) {
            return
        }
        // a cycle that is running now may have looked for text before it was written, so the next one has to complete
        val targets = readers.map { it to it.started + 1 }
        targets.forEach { (reader, _) -> reader.wake() }
        val deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(timeoutMillis)
        lock.withLock {
            while (!terminated() && targets.any { (reader, target) -> !reader.stopped && reader.completed < target }) {
                val left = deadline - System.nanoTime()
                if (left <= 0) {
                    return
                }
                cycleCompleted.awaitNanos(left)
            }
        }
    }
}

/**
 * The process handler of Robot Framework runs. Its output readers count their read cycles for the [outputFence], so
 * that the text that the process wrote before a debugger event reaches the results before the event. Stop asks the
 * debugger of the run to end it, through [terminate], which returns null without a connection to the debugger.
 */
class RobotCodeProcessHandler(
    process: Process, commandLine: String, charset: Charset, terminate: () -> CompletableFuture<*>?
) : KillableColoredProcessHandler(process, commandLine, charset) {

    // not already while the process is terminating: a stopped run still runs its teardowns, whose output keeps its order
    internal val outputFence = OutputFence { isProcessTerminated }

    private val stopPolicy = RobotCodeStopPolicy(
        terminate,
        fallback = { super.doDestroyProcess() },
        schedule = { delayMillis, task ->
            AppExecutorUtil.getAppScheduledExecutorService()
                .schedule(Runnable { task() }, delayMillis, TimeUnit.MILLISECONDS)
        },
    )

    /** Completes once a stop of the run has settled; see [RobotCodeStopPolicy.settled]. */
    internal val stopSettled: CompletableFuture<Unit>
        get() = stopPolicy.settled

    // the debugger ends the run as on Ctrl+C in a terminal, so that Robot Framework still writes its outputs; the
    // inherited destroy runs only when the debugger cannot be asked or does not answer. The second Stop kills the
    // process as before.
    override fun doDestroyProcess() {
        AppExecutorUtil.getAppExecutorService().execute { stopPolicy.stop() }
    }

    override fun createOutputDataReader(): BaseDataReader =
        CountingOutputReader(createProcessOutReader(), ProcessOutputTypes.STDOUT, "output stream of $myPresentableName")

    override fun createErrorDataReader(): BaseDataReader =
        CountingOutputReader(createProcessErrReader(), ProcessOutputTypes.STDERR, "error stream of $myPresentableName")

    // the platform's reader with counted cycles; non-blocking, because a blocking reader never reaches beforeSleeping
    private inner class CountingOutputReader(reader: Reader, private val outputType: Key<*>, name: String) :
        BaseOutputReader(reader, BaseOutputReader.Options.NON_BLOCKING), ReadCycles {

        @Volatile
        override var started = 0L
            private set

        @Volatile
        override var completed = 0L
            private set

        override val stopped: Boolean
            get() = isStopped

        init {
            outputFence.add(this)
            start(name)
        }

        override fun executeOnPooledThread(runnable: Runnable): Future<*> = executeTask(runnable)

        override fun onTextAvailable(text: String) {
            notifyTextAvailable(text, outputType)
        }

        override fun readAvailable(): Boolean {
            started++
            return super.readAvailable()
        }

        override fun beforeSleeping(hasJustReadSomething: Boolean) {
            completed = started
            outputFence.onCycleCompleted()
        }

        @Suppress("PLATFORM_CLASS_MAPPED_TO_KOTLIN")
        override fun wake() {
            synchronized(mySleepMonitor) { (mySleepMonitor as Object).notifyAll() }
        }
    }
}
