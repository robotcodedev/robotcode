package dev.robotcode.robotcode4ij.lsp

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.jetbrains.python.sdk.pythonSdk
import com.redhat.devtools.lsp4ij.server.LanguageServerLogErrorHandler
import com.redhat.devtools.lsp4ij.server.OSProcessStreamConnectionProvider
import dev.robotcode.robotcode4ij.BundledHelpers
import java.io.InputStream
import java.io.OutputStream
import java.net.ServerSocket
import java.net.Socket
import java.nio.charset.StandardCharsets
import kotlin.io.path.pathString

class RobotCodeLanguageServer(private val project: Project) : OSProcessStreamConnectionProvider(),
                                                              LanguageServerLogErrorHandler {
                                                              
    private var inputStream: InputStream? = null
    private var outputStream: OutputStream? = null
    private var serverSocket: ServerSocket? = null
    private var clientSocket: Socket? = null
    
    init {
        this.addLogErrorHandler(this)
        commandLine = buildCommandLine()
    }
    
    private fun buildCommandLine(port: Int = 6610): GeneralCommandLine {
        val pythonInterpreter = project.pythonSdk?.homePath;
        if (pythonInterpreter != null) {
            return GeneralCommandLine(
                pythonInterpreter, "-u", "-X", "utf8",
                //"-m", "robotcode.cli",
                BundledHelpers.robotCodePath.pathString,
                //"--log", "--log-level", "DEBUG",
                // "--debugpy",
                // "--debugpy-wait-for-client",
                "language-server", "--socket", "$port"
            ).withWorkDirectory(project.basePath).withCharset(StandardCharsets.UTF_8)
        }
        throw IllegalArgumentException("PythonSDK is not defined for project ${project.name}")
    }
    
    override fun logError(error: String?) {
        if (error != null)
            thisLogger().error(error)
    }
    
    // override fun getInitializationOptions(rootUri: VirtualFile?): Any {
    //     return null
    // }
    
    override fun start() {
        serverSocket = ServerSocket(0)
        commandLine = buildCommandLine(serverSocket!!.localPort)
        thisLogger().info("Start robotcode with command $commandLine")
        super.start()
        clientSocket = serverSocket!!.accept()
        inputStream = clientSocket!!.getInputStream()
        outputStream = clientSocket!!.getOutputStream()
    }
    
    override fun stop() {
        super.stop()
        inputStream = null
        outputStream = null
        clientSocket!!.close()
        clientSocket = null
        serverSocket!!.close()
        serverSocket = null;
        
    }
    override fun getInputStream(): InputStream {
        return inputStream!!
    }
    
    override fun getOutputStream(): OutputStream {
        return outputStream!!
    }
}
