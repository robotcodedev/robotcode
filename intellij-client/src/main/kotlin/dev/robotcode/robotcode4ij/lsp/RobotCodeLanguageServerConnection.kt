package dev.robotcode.robotcode4ij.lsp

import com.redhat.devtools.lsp4ij.server.CannotStartProcessException
import dev.robotcode.robotcode4ij.RobotCodeBundle
import java.io.IOException
import java.io.InputStream
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketTimeoutException
import kotlin.time.Duration
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.Duration.Companion.seconds

/**
 * The port that the language server connects to. It is bound to 127.0.0.1, the address the server connects to in socket
 * mode; `InetAddress.getLoopbackAddress()` would be `::1` when the JVM prefers IPv6.
 */
internal fun createLanguageServerListener(): ServerSocket {
    return ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"))
}

/**
 * Waits until the language server connects to [listener], and closes the listener afterwards in any case.
 *
 * Between tries, [exitCode] tells whether the server process is gone: it returns the exit code then, and `null` while
 * the process runs. A process that neither connects nor exits within [timeout] is ended with [endProcess].
 */
internal fun acceptLanguageServer(
    listener: ServerSocket,
    exitCode: () -> Int?,
    endProcess: () -> Unit,
    timeout: Duration = 60.seconds,
    pollInterval: Duration = 200.milliseconds
): Socket {
    listener.use {
        listener.soTimeout = pollInterval.inWholeMilliseconds.toInt()
        val start = System.nanoTime()
        while (true) {
            try {
                return listener.accept()
            } catch (_: SocketTimeoutException) {
            }

            exitCode()?.let {
                throw CannotStartProcessException(RobotCodeBundle.message("languageServer.start.exited", it.toString()))
            }

            if (System.nanoTime() - start >= timeout.inWholeNanoseconds) {
                endProcess()
                throw CannotStartProcessException(
                    RobotCodeBundle.message("languageServer.start.timeout", timeout.inWholeSeconds.toString())
                )
            }
        }
    }
}

/**
 * Passes each line of [input] that is not blank to [sink] until the stream ends.
 */
internal fun forwardLines(input: InputStream, sink: (String) -> Unit) {
    try {
        input.bufferedReader(Charsets.UTF_8).forEachLine { line ->
            if (line.isNotBlank()) {
                sink(line)
            }
        }
    } catch (_: IOException) {
        // a pipe whose writer ended without closing it is broken
    }
}
