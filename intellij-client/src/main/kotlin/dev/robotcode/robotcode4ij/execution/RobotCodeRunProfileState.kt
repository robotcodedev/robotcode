package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.CantRunException
import com.intellij.execution.DefaultExecutionResult
import com.intellij.execution.ExecutionException
import com.intellij.execution.ExecutionResult
import com.intellij.execution.Executor
import com.intellij.execution.configurations.CommandLineState
import com.intellij.execution.process.KillableColoredProcessHandler
import com.intellij.execution.process.ProcessEvent
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.process.ProcessListener
import com.intellij.execution.process.ProcessTerminatedListener
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.runners.ProgramRunner
import com.intellij.execution.testframework.sm.SMTestRunnerConnectionUtil
import com.intellij.execution.testframework.sm.runner.SMRunnerConsolePropertiesProvider
import com.intellij.execution.testframework.sm.runner.SMTRunnerConsoleProperties
import com.intellij.execution.testframework.ui.BaseTestsOutputConsoleView
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.util.Key
import com.intellij.openapi.util.Ref
import com.jetbrains.rd.util.reactive.Signal
import com.jetbrains.rd.util.reactive.adviseEternal
import dev.robotcode.robotcode4ij.buildRobotCodeCommandLine
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProgramRunner
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProtocolClient
import dev.robotcode.robotcode4ij.utils.NetUtils.findFreePort
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import org.eclipse.lsp4j.debug.ConfigurationDoneArguments
import org.eclipse.lsp4j.debug.InitializeRequestArguments
import org.eclipse.lsp4j.debug.launch.DSPLauncher
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.Launcher
import java.net.Socket
import java.net.SocketTimeoutException
import kotlin.uuid.ExperimentalUuidApi
import kotlin.uuid.Uuid


class RobotCodeRunProfileState(private val config: RobotCodeRunConfiguration, environment: ExecutionEnvironment) :
    CommandLineState(environment), ProcessListener {
    
    companion object {
        const val DEBUGGER_DEFAULT_PORT = 6612
        val DEBUG_PORT: Key<Int> = Key.create("ROBOTCODE_DEBUG_PORT")
        const val TESTFRAMEWORK_NAME = "RobotCode"
    }
    
    val debugClient = RobotCodeDebugProtocolClient()
    lateinit var debugServer: IDebugProtocolServer
    var isInitialized = false
        private set
    var isConfigurationDone = false
        private set
    
    val afterInitialize = Signal<Unit>()
    val afterConfigurationDone = Signal<Unit>()
    
    
    init {
        debugClient.onTerminated.adviseEternal {
            if (socket.isConnected) socket.close()
        }
    }
    
    private lateinit var socket: Socket
    
    override fun startProcess(): ProcessHandler {
        val project = environment.project
        val profile =
            environment.runProfile as? RobotCodeRunConfiguration ?: throw CantRunException("Invalid run configuration")
        
        // TODO: Add support for configurable paths
        val defaultPaths = arrayOf("--default-path", ".")
        
        val debug = environment.runner is RobotCodeDebugProgramRunner
        
        val included = mutableListOf<String>()
        for (test in profile.includedTestItems) {
            included.add("--by-longname")
            included.add(test.longname)
        }
        
        val connection = mutableListOf<String>()
        
        val port = findFreePort(DEBUGGER_DEFAULT_PORT)
        if (port != DEBUGGER_DEFAULT_PORT) {
            included.add("--tcp")
            included.add(port.toString())
        }
        
        val commandLine = project.buildRobotCodeCommandLine(
            arrayOf(
                *defaultPaths,
                "debug",
                *connection.toTypedArray(),
                *(if (!debug) arrayOf("--no-debug") else arrayOf()),
                *(included.toTypedArray())
            ), noColor = false ,extraArgs = arrayOf("-v", "--log", "--log-level", "TRACE")
        
        )
        
        val handler = KillableColoredProcessHandler(commandLine) // handler.setHasPty(true)
        handler.putUserData(DEBUG_PORT, port)
        ProcessTerminatedListener.attach(handler)
        handler.addProcessListener(this)
        
        // RunContentManager.getInstance(project).showRunContent(environment.executor, handler)
        
        return handler
    }
    
    override fun execute(executor: Executor, runner: ProgramRunner<*>): ExecutionResult {
        val processHandler = startProcess()
        val (console, properties) = createAndAttachConsoleInEDT(processHandler, executor)
        
        val result = DefaultExecutionResult(console, processHandler, *createActions(console, processHandler))
        result.setRestartActions(properties.createRerunFailedTestsAction(console))
        
        return result
    }
    
    
    private fun createAndAttachConsoleInEDT(
        processHandler: ProcessHandler, executor: Executor
    ): Pair<BaseTestsOutputConsoleView, SMTRunnerConsoleProperties> {
        val consoleRef = Ref.create<Any>()
        val propertiesRef = Ref.create<Any>()
        ApplicationManager.getApplication().invokeAndWait {
            try {
                val propertiesProvider = config as SMRunnerConsolePropertiesProvider
                
                val consoleProperties = propertiesProvider.createTestConsoleProperties(executor)
                if (consoleProperties is RobotRunnerConsoleProperties) {
                    consoleProperties.state = this
                }
                
                var splitterPropertyName = SMTestRunnerConnectionUtil.getSplitterPropertyName(TESTFRAMEWORK_NAME)
                var consoleView = RobotCodeRunnerConsoleView(consoleProperties, splitterPropertyName)
                SMTestRunnerConnectionUtil.initConsoleView(consoleView, TESTFRAMEWORK_NAME)
                consoleView.attachToProcess(processHandler)
                consoleRef.set(consoleView)
                // consoleRef.set(createAndAttachConsole("RobotCode", processHandler, consoleProperties))
                propertiesRef.set(consoleProperties)
                
            } catch (e: ExecutionException) {
                consoleRef.set(e)
            } catch (e: RuntimeException) {
                consoleRef.set(e)
            }
        }
        
        if (consoleRef.get() is ExecutionException) {
            throw consoleRef.get() as ExecutionException
        } else if (consoleRef.get() is RuntimeException) throw consoleRef.get() as RuntimeException
        
        return Pair(consoleRef.get() as BaseTestsOutputConsoleView, propertiesRef.get() as SMTRunnerConsoleProperties)
    }
    
    private suspend fun tryConnectToServerWithTimeout(
        host: String, port: Int, timeoutMillis: Long, retryIntervalMillis: Long
    ): Socket? {
        return try {
            withTimeout(timeoutMillis) {
                var socket: Socket? = null
                while (socket == null || !socket.isConnected) {
                    socket = null
                    try {
                        socket = withContext(Dispatchers.IO) {
                            Socket(host, port)
                        }
                    } catch (_: SocketTimeoutException) {
                    } catch (_: Exception) {
                    }
                    delay(retryIntervalMillis)
                    
                }
                socket
            }
        } catch (e: TimeoutCancellationException) {
            null
        }
    }
    
    @OptIn(ExperimentalUuidApi::class) override fun startNotified(event: ProcessEvent) {
        runBlocking(Dispatchers.IO) {
            
            var port = event.processHandler.getUserData(DEBUG_PORT) ?: throw CantRunException("No debug port found.")
            
            socket = tryConnectToServerWithTimeout("127.0.0.1", port, 10000, retryIntervalMillis = 100)
                ?: throw CantRunException("Unable to establish connection to debug server.")
            
            val launcher: Launcher<IDebugProtocolServer> =
                DSPLauncher.createClientLauncher(debugClient, socket.getInputStream(), socket.getOutputStream())
            
            launcher.startListening()
            
            debugServer = launcher.remoteProxy
            
            val arguments = InitializeRequestArguments().apply {
                clientID = Uuid.random().toString()
                adapterID = Uuid.random().toString()
                
                clientName = "RobotCode4IJ"
                locale = "en_US"
                
                supportsRunInTerminalRequest = false
                supportsStartDebuggingRequest = false
                pathFormat = "path"
                supportsVariableType = true
                supportsVariablePaging = false
                
                linesStartAt1 = true
                columnsStartAt1 = true
            }
            
            val response = debugServer.initialize(arguments).await()
            isInitialized = true
            
            afterInitialize.fire(Unit)
            
            if (response.supportsConfigurationDoneRequest) {
                debugServer.configurationDone(ConfigurationDoneArguments()).await()
                isConfigurationDone = true
            }
            
            afterConfigurationDone.fire(Unit)
            debugServer.attach(emptyMap<String, Object>())
        }
    }
    
    override fun processTerminated(event: ProcessEvent) {
        if (socket.isConnected) socket.close()
    }
}
