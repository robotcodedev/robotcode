package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.process.NopProcessHandler
import com.intellij.execution.process.ProcessEvent
import com.intellij.execution.process.ProcessListener
import com.intellij.openapi.util.Key
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.InetAddress
import java.net.ServerSocket
import java.util.Collections
import java.util.concurrent.CompletableFuture
import java.util.concurrent.TimeUnit

class RobotCodeDebuggerConnectTest {

    // a started process that records what is written to its console
    private class StartedProcess {
        val handler = NopProcessHandler()
        val text: MutableList<String> = Collections.synchronizedList(mutableListOf<String>())

        init {
            handler.addProcessListener(object : ProcessListener {
                override fun onTextAvailable(event: ProcessEvent, outputType: Key<*>) {
                    text.add(event.text)
                }
            })
            handler.startNotify()
        }
    }

    // nothing listens on a port that the operating system had free a moment ago
    private val unusedPort = freeDebugPort()

    @Test
    fun aDebuggerThatDoesNotAcceptTheConnectionEndsTheProcessWithAMessage() {
        val process = StartedProcess()

        val socket = runBlocking { connectDebugger(process.handler, unusedPort, timeoutMillis = 300, retryMillis = 50) }

        assertNull(socket)
        assertTrue(process.handler.waitFor(5000))
        assertEquals(
            listOf("The RobotCode debugger did not accept the connection within 0 seconds, so the run ends.\n"),
            process.text.toList()
        )
    }

    @Test
    fun aProcessThatEndsCancelsThePendingConnectQuietly() {
        val process = StartedProcess()
        val run = RobotCodeRunScope()
        process.handler.addProcessListener(run)

        val connect = run.scope.async { connectDebugger(process.handler, unusedPort, timeoutMillis = 60_000) }
        process.handler.destroyProcess()

        runBlocking { withTimeout(5000) { connect.join() } }
        assertTrue(connect.isCancelled)
        assertTrue(process.text.isEmpty())
    }

    @Test
    fun aDebuggerThatListensLaterIsConnected() {
        val process = StartedProcess()
        val port = freeDebugPort()
        // the debugger of a run listens a moment after its process has started
        val listening = CompletableFuture.supplyAsync({
            ServerSocket(port, 1, InetAddress.getByName("127.0.0.1")).also { it.accept().close() }
        }, CompletableFuture.delayedExecutor(300, TimeUnit.MILLISECONDS))

        val socket = runBlocking { connectDebugger(process.handler, port, timeoutMillis = 5000, retryMillis = 50) }

        assertNotNull(socket)
        socket?.close()
        listening.get(5, TimeUnit.SECONDS).close()
        assertFalse(process.handler.isProcessTerminated)
        assertTrue(process.text.isEmpty())
        process.handler.destroyProcess()
    }
}
