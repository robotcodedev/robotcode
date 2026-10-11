package dev.robotcode.robotcode4ij.debugging

import dev.robotcode.robotcode4ij.execution.handshake
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import org.eclipse.lsp4j.debug.Capabilities
import org.eclipse.lsp4j.debug.ConfigurationDoneArguments
import org.eclipse.lsp4j.debug.InitializeRequestArguments
import org.eclipse.lsp4j.debug.SetBreakpointsArguments
import org.eclipse.lsp4j.debug.SetBreakpointsResponse
import org.eclipse.lsp4j.debug.SetExceptionBreakpointsArguments
import org.eclipse.lsp4j.debug.SetExceptionBreakpointsResponse
import org.eclipse.lsp4j.debug.Source
import org.eclipse.lsp4j.debug.launch.DSPLauncher
import org.eclipse.lsp4j.debug.services.IDebugProtocolClient
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.debug.DebugLauncher
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.TimeUnit

class RobotCodeDebugHandshakeTest {

    // a debugger that records the requests it gets; it answers setBreakpoints after a delay
    private class FakeDebugger(private val sendsInitialized: Boolean) : IDebugProtocolServer {
        val requests = CopyOnWriteArrayList<String>()
        lateinit var client: IDebugProtocolClient

        override fun initialize(args: InitializeRequestArguments): CompletableFuture<Capabilities> {
            requests.add("initialize")
            // as the RobotCode debugger does, the event goes out before the response
            if (sendsInitialized) client.initialized()
            return CompletableFuture.completedFuture(Capabilities().apply { supportsConfigurationDoneRequest = true })
        }

        override fun setBreakpoints(args: SetBreakpointsArguments): CompletableFuture<SetBreakpointsResponse> {
            requests.add("setBreakpoints ${args.source.path}")
            return CompletableFuture.supplyAsync({
                requests.add("setBreakpoints response ${args.source.path}")
                SetBreakpointsResponse().apply { breakpoints = arrayOf() }
            }, CompletableFuture.delayedExecutor(100, TimeUnit.MILLISECONDS))
        }

        override fun setExceptionBreakpoints(
            args: SetExceptionBreakpointsArguments
        ): CompletableFuture<SetExceptionBreakpointsResponse> {
            requests.add("setExceptionBreakpoints")
            return CompletableFuture.completedFuture(SetExceptionBreakpointsResponse())
        }

        override fun attach(args: MutableMap<String, Any>): CompletableFuture<Void> {
            requests.add("attach")
            return CompletableFuture.completedFuture(null)
        }

        override fun configurationDone(args: ConfigurationDoneArguments): CompletableFuture<Void> {
            requests.add("configurationDone")
            return CompletableFuture.completedFuture(null)
        }
    }

    private val sockets = mutableListOf<AutoCloseable>()

    @After
    fun closeSockets() {
        sockets.forEach { it.close() }
    }

    // connects a client to [debugger] over a local socket, as the run state connects to the RobotCode debugger
    private fun connect(debugger: FakeDebugger, client: RobotCodeDebugProtocolClient): IRobotCodeDebugProtocolServer {
        val serverSocket = ServerSocket(0, 1, InetAddress.getLoopbackAddress()).also { sockets.add(it) }
        val accepted = CompletableFuture.supplyAsync {
            serverSocket.accept().also { socket ->
                sockets.add(socket)
                val launcher = DSPLauncher.createServerLauncher(debugger, socket.getInputStream(), socket.getOutputStream())
                debugger.client = launcher.remoteProxy
                launcher.startListening()
            }
        }
        val socket = Socket(InetAddress.getLoopbackAddress(), serverSocket.localPort).also { sockets.add(it) }
        accepted.get(5, TimeUnit.SECONDS)
        val launcher = DebugLauncher.createLauncher(
            client, IRobotCodeDebugProtocolServer::class.java, socket.getInputStream(), socket.getOutputStream()
        )
        launcher.startListening()
        return launcher.remoteProxy
    }

    private fun millisOf(block: () -> Unit): Long {
        val start = System.nanoTime()
        block()
        return TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - start)
    }

    @Test
    fun theInitializedEventBeforeTheResponseEndsTheWait() {
        val debugger = FakeDebugger(sendsInitialized = true)
        val client = RobotCodeDebugProtocolClient()
        val server = connect(debugger, client)

        val millis = millisOf { runBlocking { handshake(server, client, configure = null, initializedTimeoutMillis = 5000) } }

        assertTrue(client.initializedEvent.isDone)
        assertTrue("took $millis ms", millis < 2000)
        assertEquals(listOf("initialize", "attach", "configurationDone"), debugger.requests.toList())
    }

    @Test
    fun withoutTheInitializedEventTheHandshakeGoesOnAfterTheTimeout() {
        val debugger = FakeDebugger(sendsInitialized = false)
        val client = RobotCodeDebugProtocolClient()
        val server = connect(debugger, client)

        val millis = millisOf { runBlocking { handshake(server, client, configure = null, initializedTimeoutMillis = 300) } }

        assertTrue("took $millis ms", millis >= 300)
        assertEquals(listOf("initialize", "attach", "configurationDone"), debugger.requests.toList())
    }

    @Test
    fun theConfigurationIsCompleteBeforeAttachAndConfigurationDone() {
        val debugger = FakeDebugger(sendsInitialized = true)
        val client = RobotCodeDebugProtocolClient()
        val server = connect(debugger, client)

        runBlocking {
            handshake(server, client, configure = {
                for (file in listOf("a.robot", "b.robot")) {
                    server.setBreakpoints(SetBreakpointsArguments().apply {
                        source = Source().apply { path = file }
                        breakpoints = arrayOf()
                    }).await()
                }
                server.setExceptionBreakpoints(SetExceptionBreakpointsArguments().apply { filters = arrayOf() }).await()
            })
        }

        assertEquals(
            listOf(
                "initialize",
                "setBreakpoints a.robot",
                "setBreakpoints response a.robot",
                "setBreakpoints b.robot",
                "setBreakpoints response b.robot",
                "setExceptionBreakpoints",
                "attach",
                "configurationDone",
            ),
            debugger.requests.toList()
        )
    }
}
