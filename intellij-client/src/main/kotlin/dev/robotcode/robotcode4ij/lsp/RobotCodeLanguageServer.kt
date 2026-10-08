package dev.robotcode.robotcode4ij.lsp

import com.intellij.execution.CantRunException
import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.redhat.devtools.lsp4ij.server.CannotStartProcessException
import com.redhat.devtools.lsp4ij.server.LanguageServerLogErrorHandler
import com.redhat.devtools.lsp4ij.server.OSProcessStreamConnectionProvider
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettingsMapper
import java.io.InputStream
import java.io.OutputStream
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Starts the language server and connects to it through a local socket. [commandLineFor] builds the command line for
 * the port that the server connects to.
 */
class RobotCodeLanguageServer(
    private val project: Project,
    private val commandLineFor: (port: Int) -> GeneralCommandLine = { port ->
        project.buildRobotCodeCommandLine(
            arrayOf("language-server", "--socket", "$port"),
            extraArgs = RobotCodePersonalConfiguration.getInstance(project).languageServerExtraArgsList.toTypedArray()
        )
    }
) : OSProcessStreamConnectionProvider() {

    private val logHandlers = CopyOnWriteArrayList<LanguageServerLogErrorHandler>()
    private val connected = AtomicBoolean(false)
    private val stopped = AtomicBoolean(false)

    private var inputStream: InputStream? = null
    private var outputStream: OutputStream? = null
    private var listener: ServerSocket? = null
    private var clientSocket: Socket? = null

    override fun getInitializationOptions(rootUri: VirtualFile?): Any {
        return RobotCodeServerSettingsMapper.toInitializationOptions(project)
    }

    // LSP4IJ writes the server's stderr into the server's log through the handlers it registers here; stdout goes to
    // them as well
    override fun addLogErrorHandler(handler: LanguageServerLogErrorHandler) {
        logHandlers.add(handler)
        super.addLogErrorHandler(handler)
    }

    // A process that ends before it connects fails start() with its exit code. And stop() lets the process end by
    // itself before the base stop() marks the provider as stopped. LSP4IJ would take both for an unexpected stop.
    override fun addUnexpectedServerStopHandler(handler: Runnable) {
        super.addUnexpectedServerStopHandler {
            if (connected.get() && !stopped.get()) {
                handler.run()
            }
        }
    }

    override fun start() {
        try {
            startAndConnect()
        } catch (e: Exception) {
            // Without it, LSP4IJ would start the server again for every editor that needs it. A stop during the start,
            // for a restart or because the project closes, is no failed start.
            if (!stopped.get()) {
                project.langServerManager.reportStartFailure()
            }
            throw if (e is CantRunException) CannotStartProcessException(e.message) else e
        }
    }

    private fun startAndConnect() {
        val listener = createLanguageServerListener()
        this.listener = listener
        try {
            commandLine = commandLineFor(listener.localPort)
            thisLogger().info("Start robotcode language server with command $commandLine")
            super.start()
        } catch (e: Exception) {
            // no server will connect
            listener.close()
            throw e
        }

        // LSP4IJ copies stdout into a pipe that nothing reads, because the protocol goes through the socket; a server
        // that prints a lot would block once the pipe is full
        val stdout = super.getInputStream()
        ApplicationManager.getApplication().executeOnPooledThread {
            forwardLines(stdout) { line -> logHandlers.forEach { it.logError(line) } }
        }

        val process = processHandler.process
        val socket = acceptLanguageServer(
            listener,
            exitCode = { if (process.isAlive) null else process.exitValue() },
            endProcess = { process.destroy() }
        )
        clientSocket = socket
        inputStream = socket.getInputStream()
        outputStream = socket.getOutputStream()
        connected.set(true)
    }

    override fun stop() {
        if (!stopped.compareAndSet(false, true)) {
            return
        }

        // On a stop or restart, LSP4IJ sends the exit notification and calls stop() on a pooled thread, and the server
        // ends by itself. When the project closes, LSP4IJ calls stop() on the EDT without the exit notification.
        if (!ApplicationManager.getApplication().isDispatchThread) {
            processHandler?.process?.waitFor(2, TimeUnit.SECONDS)
        }

        inputStream = null
        outputStream = null
        clientSocket?.close()
        clientSocket = null
        listener?.close()
        listener = null
        super.stop()
    }

    override fun getInputStream(): InputStream {
        return inputStream!!
    }

    override fun getOutputStream(): OutputStream {
        return outputStream!!
    }
}
