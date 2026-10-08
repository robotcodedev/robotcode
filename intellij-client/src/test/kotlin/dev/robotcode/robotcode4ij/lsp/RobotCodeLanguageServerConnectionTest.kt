package dev.robotcode.robotcode4ij.lsp

import com.redhat.devtools.lsp4ij.server.CannotStartProcessException
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.ByteArrayInputStream
import java.net.Socket
import kotlin.concurrent.thread
import kotlin.time.Duration.Companion.milliseconds

class RobotCodeLanguageServerConnectionTest {

    @Test
    fun listenerIsBoundToTheLoopbackAddress() {
        createLanguageServerListener().use {
            assertEquals("127.0.0.1", it.inetAddress.hostAddress)
        }
    }

    @Test
    fun connectingServerGetsASocketAndTheListenerIsClosedAfterwards() {
        val listener = createLanguageServerListener()
        val client = thread { Socket("127.0.0.1", listener.localPort).use { Thread.sleep(500) } }

        acceptLanguageServer(listener, exitCode = { null }, endProcess = { fail("the process was ended") }).use {
            assertTrue(it.isConnected)
        }

        assertTrue(listener.isClosed)
        client.join()
    }

    @Test
    fun serverThatExitedBeforeItConnectedFailsTheStartWithItsExitCode() {
        val listener = createLanguageServerListener()

        val error = assertThrows(CannotStartProcessException::class.java) {
            acceptLanguageServer(listener, exitCode = { 3 }, endProcess = { fail("the process was ended") })
        }

        assertTrue(error.message, error.message!!.contains("3"))
        assertTrue(listener.isClosed)
    }

    @Test
    fun serverThatNeitherConnectsNorExitsIsEndedAfterTheTimeLimit() {
        val listener = createLanguageServerListener()
        var ended = false

        val error = assertThrows(CannotStartProcessException::class.java) {
            acceptLanguageServer(
                listener,
                exitCode = { null },
                endProcess = { ended = true },
                timeout = 300.milliseconds,
                pollInterval = 50.milliseconds
            )
        }

        assertTrue(ended)
        assertTrue(error.message, error.message!!.contains("did not connect"))
        assertTrue(listener.isClosed)
    }

    @Test
    fun everyLineOfALargeOutputReachesTheSink() {
        val lines = (1..4000).map { "line $it of the output of a library that prints while it is imported" }
        val output = lines.joinToString("\n", postfix = "\n").toByteArray()
        assertTrue(output.size > 200 * 1024)
        val received = mutableListOf<String>()

        forwardLines(ByteArrayInputStream(output)) { received.add(it) }

        assertEquals(lines, received)
    }
}
