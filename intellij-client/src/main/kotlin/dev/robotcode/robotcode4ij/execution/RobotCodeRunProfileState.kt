package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.CantRunException
import com.intellij.execution.DefaultExecutionResult
import com.intellij.execution.ExecutionException
import com.intellij.execution.ExecutionResult
import com.intellij.execution.Executor
import com.intellij.execution.process.KillableColoredProcessHandler
import com.intellij.execution.process.ProcessEvent
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.process.ProcessListener
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.target.TargetEnvironment
import com.intellij.execution.target.TargetedCommandLine
import com.intellij.execution.testframework.sm.SMTestRunnerConnectionUtil
import com.intellij.execution.testframework.sm.runner.SMTRunnerConsoleProperties
import com.intellij.execution.testframework.ui.BaseTestsOutputConsoleView
import com.intellij.execution.util.ProgramParametersConfigurator
import com.intellij.execution.ui.ConsoleView
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Key
import com.jetbrains.python.run.PythonCommandLineState
import com.jetbrains.python.run.PythonExecution
import com.jetbrains.python.run.PythonScriptExecution
import com.jetbrains.python.run.target.HelpersAwareTargetEnvironmentRequest
import com.jetbrains.rd.util.reactive.Signal
import com.jetbrains.rd.util.reactive.adviseEternal
import dev.robotcode.robotcode4ij.InterpreterKind
import dev.robotcode.robotcode4ij.PythonInterpreter
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotCodeHelpers
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.debugging.IRobotCodeDebugProtocolServer
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProgramRunner
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProtocolClient
import dev.robotcode.robotcode4ij.pythonInterpreterOf
import dev.robotcode.robotcode4ij.robotCodeArguments
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
import java.util.function.Function
import kotlin.io.path.pathString
import kotlin.uuid.ExperimentalUuidApi
import kotlin.uuid.Uuid

/**
 * The arguments after `debug`: the options of `robotcode debug`, then a `--` separator and the arguments for Robot
 * Framework, only when there are any.
 */
internal fun debugArguments(debug: Boolean, port: Int, robotArguments: List<String>): List<String> {
    return buildList {
        if (!debug) {
            add("--no-debug")
        }
        if (port != RobotCodeRunProfileState.DEBUGGER_DEFAULT_PORT) {
            addAll(listOf("--tcp", port.toString()))
        }
        if (robotArguments.isNotEmpty()) {
            add("--")
            addAll(robotArguments)
        }
    }
}

/**
 * The arguments of a run after the bundled `robotcode`: the global options as for the other `robotcode` commands, with
 * the selected [profiles] but without the robotcode extra args, as in VS Code, then `-dp . debug` and [debugArguments].
 */
internal fun runArguments(
    profiles: List<String>, debug: Boolean, port: Int, robotArguments: List<String>
): List<String> {
    return robotCodeArguments(
        extraArgs = listOf(), format = "", noColor = false, noPager = true, profiles = profiles,
        args = listOf("-dp", ".", "debug") + debugArguments(debug, port, robotArguments)
    )
}

/** The reason why a run cannot use [interpreter], or null when it can. */
internal fun interpreterRefusal(interpreter: PythonInterpreter): String? {
    return if (interpreter.kind == InterpreterKind.REMOTE) RobotCodeBundle.message("run.remoteInterpreter") else null
}

/**
 * Starts a Robot Framework run through PyCharm's target-aware Python execution, so the configuration's interpreter,
 * environment, working directory and `PYTHONPATH` options apply, and connects to the RobotCode debugger of the run.
 */
class RobotCodeRunProfileState(private val config: RobotCodeRunConfiguration, environment: ExecutionEnvironment) :
    PythonCommandLineState(config, environment), ProcessListener {
    
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
    
    private var debugPort = DEBUGGER_DEFAULT_PORT
    
    private var consoleProperties: SMTRunnerConsoleProperties? = null
    
    override fun buildPythonExecution(helpersAwareRequest: HelpersAwareTargetEnvironmentRequest): PythonExecution {
        interpreterRefusal(pythonInterpreterOf(sdk))?.let { throw ExecutionException(it) }
        
        val project = environment.project
        val debug = environment.runner is RobotCodeDebugProgramRunner
        val testManager = project.testManger
        // the macros of the stored values, expanded with the data context of the run
        val configurator = ProgramParametersConfigurator()
        val robotArguments = robotFrameworkArguments(
            config.options, testManager.testItems, testManager.supportsParseInclude,
            expandPath = { configurator.expandPathAndMacros(it, config.module, project) ?: it },
            parseArguments = { ProgramParametersConfigurator.expandMacrosAndParseParameters(it) }
        )
        debugPort = findFreePort(DEBUGGER_DEFAULT_PORT)
        
        return PythonScriptExecution().apply {
            pythonScriptPath = Function { RobotCodeHelpers.robotCodePath.pathString }
            additionalInterpreterParameters.addAll(listOf("-u", "-X", "utf8"))
            charset = Charsets.UTF_8
            val profiles = RobotCodePersonalConfiguration.getInstance(project).profiles.toList()
            addParameters(runArguments(profiles, debug, debugPort, robotArguments))
        }
    }
    
    override fun createProcessHandler(
        process: Process, commandLine: String, targetEnvironment: TargetEnvironment,
        targetedCommandLine: TargetedCommandLine
    ): ProcessHandler {
        val handler = KillableColoredProcessHandler(process, commandLine, targetedCommandLine.charset)
        handler.putUserData(DEBUG_PORT, debugPort)
        handler.addProcessListener(this)
        return handler
    }
    
    override fun createAndAttachConsole(
        project: Project, processHandler: ProcessHandler, executor: Executor
    ): ConsoleView {
        val properties = config.createTestConsoleProperties(executor)
        if (properties is RobotRunnerConsoleProperties) {
            properties.state = this
        }
        
        val splitterPropertyName = SMTestRunnerConnectionUtil.getSplitterPropertyName(TESTFRAMEWORK_NAME)
        val consoleView = RobotCodeRunnerConsoleView(properties, splitterPropertyName)
        SMTestRunnerConnectionUtil.initConsoleView(consoleView, TESTFRAMEWORK_NAME)
        consoleView.attachToProcess(processHandler)
        consoleProperties = properties
        return consoleView
    }
    
    override fun execute(executor: Executor): ExecutionResult? {
        val result = super.execute(executor) ?: return null
        val console = result.executionConsole
        val properties = consoleProperties
        if (result is DefaultExecutionResult && console is BaseTestsOutputConsoleView && properties != null) {
            result.setRestartActions(properties.createRerunFailedTestsAction(console))
        }
        return result
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
