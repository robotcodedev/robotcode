package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.CantRunException
import com.intellij.execution.DefaultExecutionResult
import com.intellij.execution.ExecutionException
import com.intellij.execution.ExecutionResult
import com.intellij.execution.Executor
import com.intellij.execution.configurations.CommandLineState
import com.intellij.execution.configurations.GeneralCommandLine
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
import dev.robotcode.robotcode4ij.debugging.IRobotCodeDebugProtocolServer
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProgramRunner
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProtocolClient
import dev.robotcode.robotcode4ij.testing.testManger
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
import org.eclipse.lsp4j.jsonrpc.debug.DebugLauncher
import java.net.Socket
import java.net.SocketTimeoutException
import kotlin.io.path.Path
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
    lateinit var debugServer: IRobotCodeDebugProtocolServer
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
        val profile = environment.runProfile as? RobotCodeRunConfiguration
            ?: throw CantRunException("Invalid run configuration")
        
        // Determine default paths
        val testSuitePath = profile.testSuitePath
        
        // TODO: Add support for configurable paths
        val defaultPaths = arrayOf("-dp", ".")
        
        // Prepare variables as command line arguments
        val variables = profile.variables?.split(",")?.mapNotNull {
            val keyValue = it.split("=")
            if (keyValue.size == 2) "-v ${keyValue[0]}:${keyValue[1]}" else null
        }?.toTypedArray() ?: emptyArray()
        
        // Collect additional arguments
        val additionalArguments = profile.additionalArguments?.split(" ")?.toTypedArray() ?: emptyArray()
        
        val debug = environment.runner is RobotCodeDebugProgramRunner
        
        val included = mutableListOf<String>()

        if (testSuitePath != null){
            val testitem = profile.project.testManger.findTestItem(Path(testSuitePath).toUri().toString())
            if (testitem != null) {
                included.add("-bl")
                included.add(testitem.longname)
            }
        }
        if (!profile.includedTestItems.isNullOrEmpty()) {
            val testItemLongNames = profile.includedTestItems!!.split(",").map { it.trim() }.filter { it.isNotEmpty() }
            for (testItemLongName in testItemLongNames){
                included.add("-bl")
                included.add(testItemLongName)
            }
        }
        
        val connection = mutableListOf<String>()
        val port = findFreePort(DEBUGGER_DEFAULT_PORT)
        if (port != DEBUGGER_DEFAULT_PORT) {
            included.add("--tcp")
            included.add(port.toString())
        }
        
        // Combine all parts into the final command line
        val commandLine = project.buildRobotCodeCommandLine(
            arrayOf(
                *defaultPaths,
                "debug",
                *connection.toTypedArray(),
                *(if (!debug) arrayOf("--no-debug") else arrayOf()),
                *included.toTypedArray(),
                *variables,
                *additionalArguments
            ),
            noColor = false
        )
        
        // Apply environment variables
        val environmentVariables = profile.environmentVariables.envs
        for ((key, value) in environmentVariables) {
            commandLine.environment[key] = value
        }
        
        // Apply "passParentEnvironment" if set to false
        commandLine.withParentEnvironmentType(
            if (profile.environmentVariables.isPassParentEnvs) {
                GeneralCommandLine.ParentEnvironmentType.CONSOLE
            } else {
                GeneralCommandLine.ParentEnvironmentType.NONE
            }
        )
        
        val handler = KillableColoredProcessHandler(commandLine)
        handler.putUserData(DEBUG_PORT, port)
        ProcessTerminatedListener.attach(handler)
        handler.addProcessListener(this)
        
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
                
                val splitterPropertyName = SMTestRunnerConnectionUtil.getSplitterPropertyName(TESTFRAMEWORK_NAME)
                val consoleView = RobotCodeRunnerConsoleView(consoleProperties, splitterPropertyName)
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
            
            val port = event.processHandler.getUserData(DEBUG_PORT) ?: throw CantRunException("No debug port found.")
            
            socket = tryConnectToServerWithTimeout("127.0.0.1", port, 10000, retryIntervalMillis = 100)
                ?: throw CantRunException("Unable to establish connection to debug server.")
            
            val launcher = DebugLauncher.createLauncher(
                debugClient,
                IRobotCodeDebugProtocolServer::class.java,
                socket.getInputStream(),
                socket.getOutputStream()
            );
            
            launcher.startListening()
            
            debugServer = launcher.remoteProxy
            debugClient.server = debugServer
            
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
            debugServer.attach(emptyMap<String, Any>())
        }
    }
    
    override fun processTerminated(event: ProcessEvent) {
        if (socket.isConnected) socket.close()
    }
}
