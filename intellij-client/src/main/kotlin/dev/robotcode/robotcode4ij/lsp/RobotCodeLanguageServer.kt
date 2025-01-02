package dev.robotcode.robotcode4ij.lsp

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.project.Project
import com.redhat.devtools.lsp4ij.server.LanguageServerLogErrorHandler
import com.redhat.devtools.lsp4ij.server.OSProcessStreamConnectionProvider
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import java.io.InputStream
import java.io.OutputStream
import java.net.ServerSocket
import java.net.Socket

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
        return project.buildRobotCodeCommandLine(arrayOf("language-server", "--socket", "$port"))
    }
    
    override fun logError(error: String?) {
        if (error != null)
            thisLogger().error(error)
    }
    
    // TODO: Implement this method
    // override fun getInitializationOptions(rootUri: VirtualFile?): Any {
    //     return null
    // }
    
    override fun start() {
        serverSocket = ServerSocket(0)
        commandLine = buildCommandLine(serverSocket!!.localPort)
        thisLogger().info("Start robotcode language server with command $commandLine")
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
        serverSocket = null
        
    }
    
    override fun getInputStream(): InputStream {
        return inputStream!!
    }
    
    override fun getOutputStream(): OutputStream {
        return outputStream!!
    }
}
