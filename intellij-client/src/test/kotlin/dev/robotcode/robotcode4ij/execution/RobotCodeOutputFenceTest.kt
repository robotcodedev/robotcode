package dev.robotcode.robotcode4ij.execution

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.TimeUnit
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.thread
import kotlin.concurrent.withLock

class RobotCodeOutputFenceTest {

    // a reader that delivers its pending text once per cycle and then sleeps for a long time, unless it is woken
    private class FakeReader(private val fence: OutputFence, private val completes: Boolean = true) : ReadCycles {
        private val lock = ReentrantLock()
        private val wakeUp = lock.newCondition()
        private val pending = ConcurrentLinkedQueue<String>()
        val delivered = CopyOnWriteArrayList<String>()

        // a wake-up that arrives while the reader is busy ends its next sleep at once, so that no wake-up gets lost
        private var woken = false

        @Volatile
        override var started = 0L

        @Volatile
        override var completed = 0L

        @Volatile
        override var stopped = false

        private val loop = thread(isDaemon = true) {
            while (!stopped) {
                started++
                while (true) {
                    delivered.add(pending.poll() ?: break)
                }
                if (completes) {
                    completed = started
                    fence.onCycleCompleted()
                }
                lock.withLock {
                    if (!woken && !stopped) wakeUp.await(10, TimeUnit.SECONDS)
                    woken = false
                }
            }
        }

        fun write(text: String) {
            pending.add(text)
        }

        override fun wake() {
            lock.withLock {
                woken = true
                wakeUp.signalAll()
            }
        }

        fun close() {
            stopped = true
            wake()
            loop.join()
        }
    }

    private val readers = mutableListOf<FakeReader>()

    private fun reader(fence: OutputFence, completes: Boolean = true) =
        FakeReader(fence, completes).also { readers.add(it) }

    @After
    fun closeReaders() {
        readers.forEach { it.close() }
    }

    private fun millisOf(block: () -> Unit): Long {
        val start = System.nanoTime()
        block()
        return TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start)
    }

    @Test
    fun textWrittenBeforeTheFenceIsDeliveredWhenItReturns() {
        val fence = OutputFence(timeoutMillis = 5000) { false }
        val stdout = reader(fence).also { fence.add(it) }
        val stderr = reader(fence).also { fence.add(it) }
        // both readers have finished their first cycle
        while (stdout.completed == 0L || stderr.completed == 0L) Thread.sleep(1)

        stdout.write("Second test")
        stderr.write("[ WARN ] a warning")
        // the readers sleep for 10 s, so returning quickly means that the fence woke them
        val millis = millisOf { fence.await() }

        assertEquals(listOf("Second test"), stdout.delivered.toList())
        assertEquals(listOf("[ WARN ] a warning"), stderr.delivered.toList())
        assertTrue("took $millis ms", millis < 2000)
    }

    @Test
    fun fenceGivesUpAfterTheTimeout() {
        val fence = OutputFence(timeoutMillis = 200) { false }
        fence.add(reader(fence, completes = false))

        val millis = millisOf { fence.await() }

        assertTrue("took $millis ms", millis in 200..<2000)
    }

    @Test
    fun fenceReturnsAtOnceWhenTheProcessHasEnded() {
        val fence = OutputFence(timeoutMillis = 5000) { true }
        fence.add(reader(fence, completes = false))

        val millis = millisOf { fence.await() }

        assertTrue("took $millis ms", millis < 1000)
    }

    @Test
    fun stoppedReaderDoesNotHoldTheFence() {
        val fence = OutputFence(timeoutMillis = 5000) { false }
        val stopped = reader(fence, completes = false).also { fence.add(it) }
        stopped.stopped = true

        val millis = millisOf { fence.await() }

        assertTrue("took $millis ms", millis < 1000)
    }
}
