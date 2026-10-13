package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.DefaultExecutionResult
import com.intellij.execution.ExecutionException
import com.intellij.execution.ExecutionResult
import com.intellij.execution.Executor
import com.intellij.execution.process.ProcessEvent
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.process.ProcessListener
import com.intellij.execution.process.ProcessOutputTypes
import com.intellij.execution.runners.ExecutionEnvironment
import com.intellij.execution.target.TargetEnvironment
import com.intellij.execution.target.TargetedCommandLine
import com.intellij.execution.testframework.sm.SMTestRunnerConnectionUtil
import com.intellij.execution.testframework.sm.runner.SMTRunnerConsoleProperties
import com.intellij.execution.testframework.ui.BaseTestsOutputConsoleView
import com.intellij.execution.util.ProgramParametersConfigurator
import com.intellij.execution.ui.ConsoleView
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Key
import com.jetbrains.python.run.PythonCommandLineState
import com.jetbrains.python.run.PythonExecution
import com.jetbrains.python.run.PythonScriptExecution
import com.jetbrains.python.run.target.HelpersAwareTargetEnvironmentRequest
import dev.robotcode.robotcode4ij.InterpreterKind
import dev.robotcode.robotcode4ij.PythonInterpreter
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotCodeHelpers
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import dev.robotcode.robotcode4ij.debugging.IRobotCodeDebugProtocolServer
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProgramRunner
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProtocolClient
import dev.robotcode.robotcode4ij.debugging.awaitRequest
import dev.robotcode.robotcode4ij.defaultPathArguments
import dev.robotcode.robotcode4ij.pythonInterpreterOf
import dev.robotcode.robotcode4ij.robotCodeArguments
import dev.robotcode.robotcode4ij.robotSettings
import dev.robotcode.robotcode4ij.testing.testManger
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.future.await
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.eclipse.lsp4j.debug.ConfigurationDoneArguments
import org.eclipse.lsp4j.debug.InitializeRequestArguments
import org.eclipse.lsp4j.debug.TerminateArguments
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.debug.DebugLauncher
import java.io.IOException
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CompletableFuture
import java.util.function.Function
import kotlin.io.path.pathString
import kotlin.uuid.ExperimentalUuidApi
import kotlin.uuid.Uuid

/**
 * The arguments after `debug`: the options of `robotcode debug`, with the port of the debugger connection, then a `--`
 * separator and the arguments for Robot Framework, only when there are any.
 */
internal fun debugArguments(debug: Boolean, port: Int, robotArguments: List<String>): List<String> {
    return buildList {
        if (!debug) {
            add("--no-debug")
        }
        addAll(listOf("--tcp", port.toString()))
        if (robotArguments.isNotEmpty()) {
            add("--")
            addAll(robotArguments)
        }
    }
}

/**
 * The arguments of a run after the bundled `robotcode`: the global options as for the other `robotcode` commands, with
 * the selected [profiles] but without the robotcode extra args, as in VS Code, then the default [paths] of the "Robot"
 * settings page, which discovery passes too, `debug` and [debugArguments].
 */
internal fun runArguments(
    profiles: List<String>, paths: List<String>, debug: Boolean, port: Int, robotArguments: List<String>
): List<String> {
    return robotCodeArguments(
        extraArgs = listOf(), format = "", noColor = false, noPager = true, profiles = profiles,
        args = defaultPathArguments(paths) + listOf("debug") + debugArguments(debug, port, robotArguments)
    )
}

/**
 * The profiles that a run selects with `-p`: the [projectSelection] for [RobotRunProfilesKind.PROJECT], none for
 * [RobotRunProfilesKind.DEFAULTS], so that the `default-profiles` of `robot.toml` apply, and the configuration's
 * [names] for [RobotRunProfilesKind.CUSTOM].
 */
internal fun resolveRunProfiles(
    kind: RobotRunProfilesKind, names: List<String>, projectSelection: List<String>
): List<String> {
    return when (kind) {
        RobotRunProfilesKind.PROJECT -> projectSelection
        RobotRunProfilesKind.DEFAULTS -> listOf()
        RobotRunProfilesKind.CUSTOM -> names.map { it.trim() }.filter { it.isNotEmpty() }
    }
}

/** The environment variables of the "Robot" settings page, without pairs that have no name. */
internal fun robotEnvironment(settings: RobotCodeProjectConfiguration.ProjectState): Map<String, String> {
    return settings.robotEnv.mapKeys { it.key.trim() }.filterKeys { it.isNotEmpty() }
}

/** A port that the operating system has free now, for the debugger connection of a run. */
internal fun freeDebugPort(): Int = ServerSocket(0).use { it.localPort }

/** The reason why a run cannot use [interpreter], or null when it can. */
internal fun interpreterRefusal(interpreter: PythonInterpreter): String? {
    return if (interpreter.kind == InterpreterKind.REMOTE) RobotCodeBundle.message("run.remoteInterpreter") else null
}

@OptIn(ExperimentalUuidApi::class)
private fun initializeArguments() = InitializeRequestArguments().apply {
    clientID = Uuid.random().toString()
    adapterID = Uuid.random().toString()
    
    clientName = "RobotCode4IJ"
    locale = "en_US"
    
    supportsRunInTerminalRequest = false
    supportsStartDebuggingRequest = false
    pathFormat = "path"
    supportsVariableType = true
    supportsVariablePaging = true
    
    linesStartAt1 = true
    columnsStartAt1 = true
}

/**
 * The DAP handshake with the RobotCode debugger, with one configuration phase before the run starts: [configure] sends
 * the breakpoints once the debugger has sent `initialized`, and the debugger is attached before `configurationDone`
 * starts Robot Framework, because only an attached debugger pauses the run at a stop.
 */
internal suspend fun handshake(
    server: IDebugProtocolServer,
    client: RobotCodeDebugProtocolClient,
    configure: (suspend () -> Unit)?,
    initializedTimeoutMillis: Long = 5000,
) {
    val capabilities = server.initialize(initializeArguments()).awaitRequest()
    // the debugger accepts configuration requests at any time after `initialize`, so a missing event only delays them
    withTimeoutOrNull(initializedTimeoutMillis) { client.initializedEvent.await() }
    configure?.invoke()
    server.attach(emptyMap<String, Any>()).awaitRequest()
    if (capabilities.supportsConfigurationDoneRequest == true) {
        server.configurationDone(ConfigurationDoneArguments()).awaitRequest()
    }
}

/** As long as the RobotCode debugger waits for its client by default (`--wait-for-client-timeout`). */
internal const val DEBUGGER_CONNECT_TIMEOUT_MILLIS = 15_000L

private const val CONNECT_RETRY_MILLIS = 100L

private const val MILLIS_PER_SECOND = 1000L

/**
 * Connects to the debugger of [handler]'s process at [port], trying for at most [timeoutMillis]. When that fails while
 * the process still runs, says so in the run's console and ends the process. Returns the connection, or null.
 */
internal suspend fun connectDebugger(
    handler: ProcessHandler, port: Int, timeoutMillis: Long = DEBUGGER_CONNECT_TIMEOUT_MILLIS,
    retryMillis: Long = CONNECT_RETRY_MILLIS
): Socket? {
    val socket = withTimeoutOrNull(timeoutMillis) {
        var connected: Socket? = null
        while (connected == null) {
            connected = try {
                withContext(Dispatchers.IO) { Socket("127.0.0.1", port) }
            } catch (_: IOException) {
                delay(retryMillis)
                null
            }
        }
        connected
    }
    if (socket == null && !handler.isProcessTerminated && !handler.isProcessTerminating) {
        handler.notifyTextAvailable(
            RobotCodeBundle.message("debugger.notConnected", timeoutMillis / MILLIS_PER_SECOND) + "\n",
            ProcessOutputTypes.SYSTEM
        )
        handler.destroyProcess()
    }
    return socket
}

/**
 * Starts a Robot Framework run through PyCharm's target-aware Python execution, so the configuration's interpreter,
 * environment, working directory and `PYTHONPATH` options apply, and connects to the RobotCode debugger of the run.
 */
class RobotCodeRunProfileState(private val config: RobotCodeRunConfiguration, environment: ExecutionEnvironment) :
    PythonCommandLineState(config, environment), ProcessListener {
    
    companion object {
        val DEBUG_PORT: Key<Int> = Key.create("ROBOTCODE_DEBUG_PORT")
        const val TESTFRAMEWORK_NAME = "RobotCode"
    }
    
    val debugClient = RobotCodeDebugProtocolClient()

    // the coroutines of the run, which end with its process
    val runScope = RobotCodeRunScope()

    // the debugger, once the connection to it stands
    @Volatile
    var debugServer: IRobotCodeDebugProtocolServer? = null
        private set

    // the configuration phase of the handshake, provided by the debug process; a run without one configures nothing
    var configuration: (suspend () -> Unit)? = null

    // the handler of the started process, whose output fence orders the process output before the debugger events
    var processHandler: RobotCodeProcessHandler? = null
        private set

    // the debugger while the connection to it is up
    @Volatile
    private var connectedServer: IRobotCodeDebugProtocolServer? = null

    private var terminateResponse: CompletableFuture<Void>? = null

    @Volatile
    private var socket: Socket? = null

    init {
        debugClient.onTerminated.advise(runScope.lifetime) {
            connectedServer = null
            socket?.close()
        }
    }

    private var debugPort = 0
    
    private var consoleProperties: SMTRunnerConsoleProperties? = null
    
    override fun buildPythonExecution(helpersAwareRequest: HelpersAwareTargetEnvironmentRequest): PythonExecution {
        interpreterRefusal(pythonInterpreterOf(sdk))?.let { throw ExecutionException(it) }
        
        val project = environment.project
        val debug = environment.runner is RobotCodeDebugProgramRunner
        val testManager = project.testManger
        // the macros of the stored values, expanded with the data context of the run
        val configurator = ProgramParametersConfigurator()
        val settings = project.robotSettings
        val robotArguments = robotFrameworkArguments(
            mergeRobotOptions(settings, config.options), testManager.testItems, testManager.supportsParseInclude,
            expandPath = { configurator.expandPathAndMacros(it, config.module, project) ?: it },
            parseArguments = { ProgramParametersConfigurator.expandMacrosAndParseParameters(it) }
        )
        // a port of its own for every run, so that runs started at the same time don't share one
        debugPort = freeDebugPort()
        
        return PythonScriptExecution().apply {
            pythonScriptPath = Function { RobotCodeHelpers.robotCodePath.pathString }
            additionalInterpreterParameters.addAll(listOf("-u", "-X", "utf8"))
            charset = Charsets.UTF_8
            // the project selection as it is now, so that a change of it reaches existing configurations
            val profiles = resolveRunProfiles(
                config.options.profilesKind, config.options.profiles,
                RobotCodePersonalConfiguration.getInstance(project).profiles.toList()
            )
            addParameters(runArguments(profiles, settings.robotPaths, debug, debugPort, robotArguments))
            // PyCharm adds the configuration's environment variables and .env files afterwards, so they win
            robotEnvironment(settings).forEach { (name, value) -> addEnvironmentVariable(name, value) }
        }
    }
    
    override fun createProcessHandler(
        process: Process, commandLine: String, targetEnvironment: TargetEnvironment,
        targetedCommandLine: TargetedCommandLine
    ): ProcessHandler {
        val handler = RobotCodeProcessHandler(process, commandLine, targetedCommandLine.charset, ::requestTerminate)
        processHandler = handler
        handler.putUserData(DEBUG_PORT, debugPort)
        // the run scope first, so that the end of the process cancels it before processTerminated below looks for a
        // connection to close
        handler.addProcessListener(runScope)
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
    
    // the platform calls this on the user interface thread, so the connection is made in the background; a process that
    // ends first cancels it
    override fun startNotified(event: ProcessEvent) {
        val handler = event.processHandler
        val port = handler.getUserData(DEBUG_PORT) ?: return
        runScope.scope.launch {
            val connection = connectDebugger(handler, port) ?: return@launch
            val launcher = DebugLauncher.createLauncher(
                debugClient,
                IRobotCodeDebugProtocolServer::class.java,
                connection.getInputStream(),
                connection.getOutputStream()
            )
            val server = launcher.remoteProxy
            // a process that ended while the connection was made found no connection to close in `processTerminated`
            synchronized(this@RobotCodeRunProfileState) {
                if (!isActive) {
                    connection.close()
                    return@launch
                }
                socket = connection
                connectedServer = server
            }
            debugServer = server
            debugClient.server = server
            launcher.startListening()
            try {
                handshake(server, debugClient, configuration)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                logger<RobotCodeRunProfileState>().warn("The handshake with the RobotCode debugger failed", e)
            }
        }
    }
    
    /**
     * Asks the debugger to end the run, at most once per run, because the debugger answers a second request with
     * SIGTERM; returns its response, or null without a connection to the debugger.
     */
    @Synchronized
    fun requestTerminate(): CompletableFuture<*>? {
        terminateResponse?.let { return it }
        val server = connectedServer ?: return null
        return server.terminate(TerminateArguments().apply { restart = false }).also { terminateResponse = it }
    }

    @Synchronized
    override fun processTerminated(event: ProcessEvent) {
        connectedServer = null
        socket?.close()
    }
}
