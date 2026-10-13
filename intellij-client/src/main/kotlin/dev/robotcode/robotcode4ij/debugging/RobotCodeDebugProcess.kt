package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.ExecutionResult
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.ui.ExecutionConsole
import com.intellij.execution.ui.RunnerLayoutUi
import com.intellij.execution.ui.layout.PlaceInGrid
import com.intellij.icons.AllIcons
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.progress.ProcessCanceledException
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.ui.MessageType
import com.intellij.openapi.util.Disposer
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.xdebugger.XDebugProcess
import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.XSourcePosition
import com.intellij.xdebugger.breakpoints.SuspendPolicy
import com.intellij.xdebugger.breakpoints.XBreakpoint
import com.intellij.xdebugger.breakpoints.XBreakpointHandler
import com.intellij.xdebugger.breakpoints.XLineBreakpoint
import com.intellij.xdebugger.evaluation.XDebuggerEditorsProvider
import com.intellij.xdebugger.frame.XSuspendContext
import com.intellij.xdebugger.ui.XDebugTabLayouter
import com.jetbrains.rd.util.lifetime.Lifetime
import com.jetbrains.rd.util.threading.coroutines.adviseSuspend
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeExceptionBreakpointHandler
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeExceptionBreakpointProperties
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeFailureKind
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeLineBreakpointHandler
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeLineBreakpointProperties
import dev.robotcode.robotcode4ij.execution.RobotCodeRunProfileState
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.eclipse.lsp4j.debug.CompletionItem
import org.eclipse.lsp4j.debug.CompletionsArguments
import org.eclipse.lsp4j.debug.ContinueArguments
import org.eclipse.lsp4j.debug.EvaluateArguments
import org.eclipse.lsp4j.debug.EvaluateArgumentsContext
import org.eclipse.lsp4j.debug.NextArguments
import org.eclipse.lsp4j.debug.PauseArguments
import org.eclipse.lsp4j.debug.SetBreakpointsArguments
import org.eclipse.lsp4j.debug.Source
import org.eclipse.lsp4j.debug.SourceBreakpoint
import org.eclipse.lsp4j.debug.StackTraceArguments
import org.eclipse.lsp4j.debug.StepInArguments
import org.eclipse.lsp4j.debug.StepOutArguments
import org.eclipse.lsp4j.debug.StoppedEventArguments
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.ResponseErrorException
import java.util.concurrent.CompletableFuture
import java.util.concurrent.ExecutionException
import java.util.concurrent.TimeUnit
import java.util.concurrent.TimeoutException

private typealias LineBreakpoint = XLineBreakpoint<RobotCodeLineBreakpointProperties>
private typealias ExceptionBreakpoint = XBreakpoint<RobotCodeExceptionBreakpointProperties>

private const val COMPLETIONS_TIMEOUT_MILLIS = 3000L

class RobotCodeDebugProcess(
    private val session: XDebugSession,
    private val executionResult: ExecutionResult,
    val state: RobotCodeRunProfileState
) : XDebugProcess(session) {

    private val debugClient: RobotCodeDebugProtocolClient
        get() {
            return state.debugClient
        }

    private val debugServer: IDebugProtocolServer
        get() {
            return state.debugServer
        }

    // the breakpoints that the debugger holds, changed and sent under one lock; until the configuration phase of the
    // handshake, registering only records them
    private val lineBreakpoints = RobotCodeLineBreakpoints<LineBreakpoint, VirtualFile>(
        { it.sourcePosition?.file }, { it.line }
    )
    private val exceptionBreakpoints = RobotCodeExceptionBreakpoints<ExceptionBreakpoint> {
        RobotCodeFailureKind.of(it.properties).filterId
    }
    private val breakpointsMutex = Mutex()
    private var configured = false

    private val editorsProvider = RobotCodeXDebuggerEditorsProvider()
    private val breakpointHandlers = arrayOf(
        RobotCodeLineBreakpointHandler(this),
        RobotCodeExceptionBreakpointHandler(this),
    )

    init {
        session.setPauseActionSupported(true)

        state.configuration = this::sendConfiguration
        debugClient.onStopped.adviseSuspend(Lifetime.Eternal, Dispatchers.IO, this::handleOnStopped)
        // a paused run that goes on, also when a stop request lets it run to its end, shows as running again; handled
        // as the event arrives, so that it cannot come after the next stop
        debugClient.onContinued.advise(Lifetime.Eternal) { session.sessionResumed() }
    }

    private suspend fun createRobotCodeSuspendContext(threadId: Int): RobotCodeSuspendContext {
        return RobotCodeSuspendContext(
            debugServer.stackTrace(StackTraceArguments().apply { this.threadId = threadId }).await(),
            threadId,
            debugServer
        )
    }

    // a stop at a failure applies the matching exception breakpoint, a stop at a line breakpoint the breakpoint the
    // debugger reports; every other stop, and a stop without a matching breakpoint, is shown as paused. A stop that the
    // session shows ends Run to Cursor, a stop that the breakpoint passes over does not.
    private suspend fun handleOnStopped(args: StoppedEventArguments) {
        val breakpoint: XBreakpoint<*>? = breakpointsMutex.withLock {
            when (args.reason) {
                "exception" -> exceptionBreakpoints.breakpointFor(args.description)
                "breakpoint" -> args.hitBreakpointIds.orEmpty().firstNotNullOfOrNull { lineBreakpoints.breakpointWithId(it) }
                else -> null
            }
        }
        val context = createRobotCodeSuspendContext(args.threadId)
        if (breakpoint == null) {
            breakpointsMutex.withLock { clearRunToCursorTarget() }
            session.positionReached(context)
        } else if (session.breakpointReached(breakpoint, evaluateLogExpression(breakpoint, context), context)) {
            breakpointsMutex.withLock { clearRunToCursorTarget() }
            if (args.reason == "exception") {
                session.reportMessage(args.text ?: args.description, MessageType.INFO)
            }
        } else {
            debugServer.continue_(ContinueArguments().apply {
                threadId = args.threadId
            }).await()
        }
    }

    // the log text of a suspending line breakpoint, evaluated like a watch in the frame the run stopped in; the debugger
    // writes the log text of a breakpoint that does not suspend itself
    private suspend fun evaluateLogExpression(breakpoint: XBreakpoint<*>, context: RobotCodeSuspendContext): String? {
        if (breakpoint !is XLineBreakpoint<*> || breakpoint.suspendPolicy == SuspendPolicy.NONE) return null
        val expression = breakpoint.logExpressionObject?.expression?.takeIf { it.isNotBlank() } ?: return null
        val frameId = context.stack.stackFrames.orEmpty().firstOrNull()?.id ?: return null
        return try {
            debugServer.evaluate(EvaluateArguments().apply {
                this.expression = expression
                this.frameId = frameId
                this.context = EvaluateArgumentsContext.WATCH
            }).await().result
        } catch (e: ResponseErrorException) {
            messageOf(e.responseError)
        }
    }

    override fun getEditorsProvider(): XDebuggerEditorsProvider {
        return editorsProvider
    }

    /**
     * The completions the debugger offers in the frame [frameId], or null if it did not answer in time. The wait ends
     * when the IDE cancels the completion, for example because the user typed on.
     */
    fun completions(frameId: Int, text: String, offset: Int): List<CompletionItem>? {
        val future = debugServer.completions(CompletionsArguments().apply {
            this.frameId = frameId
            this.text = text
            column = offset + 1
        })
        return awaitCancellable(future, COMPLETIONS_TIMEOUT_MILLIS)?.targets?.toList()
    }

    override fun createConsole(): ExecutionConsole {
        return executionResult.executionConsole
    }

    // adds the Robot Debug Console where the platform puts the run's console
    override fun createTabLayouter(): XDebugTabLayouter {
        return object : XDebugTabLayouter() {
            override fun registerAdditionalContent(ui: RunnerLayoutUi) {
                val console = RobotCodeDebugConsole(session, debugServer)
                val content = ui.createContent(
                    "RobotCodeDebugConsole", console.console.component, RobotCodeBundle.message("debugger.console.title"),
                    AllIcons.Debugger.Console, console.console.preferredFocusableComponent
                )
                content.isCloseable = false
                Disposer.register(content, console)
                ui.addContent(content, 1, PlaceInGrid.bottom, false)
            }
        }
    }

    override fun doGetProcessHandler(): ProcessHandler? {
        return executionResult.processHandler
    }

    override fun getBreakpointHandlers(): Array<out XBreakpointHandler<*>?> {
        return breakpointHandlers
    }

    fun registerExceptionBreakpoint(breakpoint: ExceptionBreakpoint) {
        runBlocking {
            breakpointsMutex.withLock {
                exceptionBreakpoints.register(breakpoint)
                if (configured) sendExceptionBreakpoints()
            }
        }
    }

    fun unregisterExceptionBreakpoint(breakpoint: ExceptionBreakpoint) {
        runBlocking {
            breakpointsMutex.withLock {
                exceptionBreakpoints.unregister(breakpoint)
                if (configured) sendExceptionBreakpoints()
            }
        }
    }

    fun registerBreakpoint(breakpoint: LineBreakpoint) {
        runBlocking {
            breakpointsMutex.withLock {
                val files = lineBreakpoints.register(breakpoint)
                if (configured) files.forEach { sendLineBreakpoints(it) }
            }
        }
    }

    fun unregisterBreakpoint(breakpoint: LineBreakpoint) {
        runBlocking {
            breakpointsMutex.withLock {
                val files = lineBreakpoints.unregister(breakpoint)
                if (configured) files.forEach { sendLineBreakpoints(it) }
            }
        }
    }

    /** Sends the list of a registered breakpoint's file again after a change of its properties, such as the hit count. */
    fun breakpointPropertiesChanged(breakpoint: LineBreakpoint) {
        runBlocking {
            breakpointsMutex.withLock {
                val file = lineBreakpoints.registeredFile(breakpoint)
                if (configured && file != null) sendLineBreakpoints(file)
            }
        }
    }

    // the configuration phase of the handshake: every breakpoint registered so far, before the run starts; a request
    // that fails does not keep the run from starting
    private suspend fun sendConfiguration() {
        breakpointsMutex.withLock {
            configured = true
            for (file in lineBreakpoints.files.filter { lineBreakpoints.entries(it).isNotEmpty() }) {
                try {
                    sendLineBreakpoints(file)
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    thisLogger().warn("The debugger did not accept the breakpoints of $file", e)
                    lineBreakpoints.entries(file).mapNotNull { it.breakpoint }.forEach {
                        session.setBreakpointInvalid(it, "Invalid breakpoint")
                    }
                }
            }
            try {
                sendExceptionBreakpoints()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                thisLogger().warn("The debugger did not accept the exception breakpoints", e)
            }
        }
    }

    // the complete list of the file, also when it is empty, so that the debugger drops what the IDE no longer shows
    private suspend fun sendLineBreakpoints(file: VirtualFile) {
        val entries = lineBreakpoints.entries(file)
        val arguments = SetBreakpointsArguments().apply {
            source = Source().apply { path = file.toNioPath().toString() }
            breakpoints = entries.map { entry ->
                val breakpoint = entry.breakpoint
                sourceBreakpoint(
                    entry.line,
                    breakpoint?.conditionExpression?.expression,
                    breakpoint?.logExpressionObject?.expression,
                    breakpoint?.properties?.hitCount,
                    breakpoint?.suspendPolicy ?: SuspendPolicy.ALL
                )
            }.toTypedArray()
        }

        val response = debugServer.setBreakpoints(arguments).await()
        lineBreakpoints.idsReceived(file, entries, response.breakpoints.orEmpty().map { it.id })

        // the debugger answers in the order of the request
        entries.zip(response.breakpoints.orEmpty()).forEach { (entry, result) ->
            val breakpoint = entry.breakpoint ?: return@forEach
            if (result.isVerified == true) {
                session.setBreakpointVerified(breakpoint)
            } else {
                session.setBreakpointInvalid(breakpoint, "Invalid breakpoint")
            }
        }
    }

    private suspend fun sendExceptionBreakpoints() {
        debugServer.setExceptionBreakpoints(exceptionBreakpoints.arguments()).await()
    }

    // called with the lock held
    private suspend fun clearRunToCursorTarget() {
        lineBreakpoints.clearTarget()?.let { if (configured) sendLineBreakpoints(it) }
    }

    // the platform calls this after the process has ended; while the connection is still up, it asks the debugger to
    // end the run, without waiting for the answer
    override fun stop() {
        ApplicationManager.getApplication().executeOnPooledThread { state.requestTerminate() }
    }

    override fun resume(context: XSuspendContext?) {
        runBlocking {
            if (context is RobotCodeSuspendContext) {
                debugServer.continue_(ContinueArguments().apply {
                    threadId = context.threadId
                }).await()
            }
        }
    }

    override fun startStepOver(context: XSuspendContext?) {
        runBlocking {
            if (context is RobotCodeSuspendContext) {
                debugServer.next(NextArguments().apply { threadId = context.threadId }).await()
            }
        }
    }

    override fun startStepInto(context: XSuspendContext?) {
        runBlocking {
            if (context is RobotCodeSuspendContext) {
                debugServer.stepIn(StepInArguments().apply {
                    threadId = context.threadId
                }).await()
            }
        }
    }

    override fun startStepOut(context: XSuspendContext?) {
        runBlocking {
            if (context is RobotCodeSuspendContext) {
                debugServer.stepOut(StepOutArguments().apply {
                    threadId = context.threadId
                }).await()
            }
        }
    }

    // always continues; a breakpoint on the target line stops the run there anyway, otherwise a temporary entry does,
    // which the next stop that the session shows removes again
    override fun runToPosition(position: XSourcePosition, context: XSuspendContext?) {
        runBlocking {
            breakpointsMutex.withLock {
                clearRunToCursorTarget()
                if (lineBreakpoints.setTarget(position.file, position.line) && configured) {
                    sendLineBreakpoints(position.file)
                }
            }
        }
        resume(context)
    }

    override fun startPausing() {
        runBlocking {
            debugServer.pause(PauseArguments().apply { threadId = 0 }).await()
        }
    }
}

/**
 * The entry for a line breakpoint in a `setBreakpoints` request. The log text goes to the debugger only for a breakpoint
 * that does not suspend: the debugger then writes it as a template at each hit and never stops. A suspending breakpoint
 * evaluates its log text when the run stops there.
 */
internal fun sourceBreakpoint(
    line: Int, condition: String?, logExpression: String?, hitCount: String?, suspendPolicy: SuspendPolicy
): SourceBreakpoint = SourceBreakpoint().apply {
    this.line = line + 1
    this.condition = condition?.takeIf { it.isNotBlank() }
    this.hitCondition = hitCount?.trim()?.takeIf { it.isNotEmpty() }
    this.logMessage = logExpression?.takeIf { it.isNotBlank() && suspendPolicy == SuspendPolicy.NONE }
}

// waits for [future] at most [timeoutMillis] and gives up, cancelling the request, when the IDE cancels the current
// operation; null if the request failed or took too long
private fun <T> awaitCancellable(future: CompletableFuture<T>, timeoutMillis: Long): T? {
    val deadline = System.currentTimeMillis() + timeoutMillis
    try {
        while (true) {
            ProgressManager.checkCanceled()
            try {
                return future.get(20, TimeUnit.MILLISECONDS)
            } catch (_: TimeoutException) {
                if (System.currentTimeMillis() >= deadline) {
                    future.cancel(true)
                    return null
                }
            }
        }
    } catch (e: ProcessCanceledException) {
        future.cancel(true)
        throw e
    } catch (_: ExecutionException) {
        return null
    }
}
