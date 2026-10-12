package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.ExecutionResult
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.ui.ExecutionConsole
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.ui.MessageType
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.xdebugger.XDebugProcess
import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.XSourcePosition
import com.intellij.xdebugger.breakpoints.XBreakpoint
import com.intellij.xdebugger.breakpoints.XBreakpointHandler
import com.intellij.xdebugger.breakpoints.XLineBreakpoint
import com.intellij.xdebugger.evaluation.XDebuggerEditorsProvider
import com.intellij.xdebugger.frame.XSuspendContext
import com.jetbrains.rd.util.lifetime.Lifetime
import com.jetbrains.rd.util.threading.coroutines.adviseSuspend
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeExceptionBreakpointHandler
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeExceptionBreakpointProperties
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeExceptionBreakpointType
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeFailedKeywordsBreakpointType
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeFailedSuitesBreakpointType
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeFailedTestsBreakpointType
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeLineBreakpointHandler
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeLineBreakpointProperties
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeUncaughtFailedKeywordsBreakpointType
import dev.robotcode.robotcode4ij.execution.RobotCodeRunProfileState
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.eclipse.lsp4j.debug.ContinueArguments
import org.eclipse.lsp4j.debug.NextArguments
import org.eclipse.lsp4j.debug.PauseArguments
import org.eclipse.lsp4j.debug.SetBreakpointsArguments
import org.eclipse.lsp4j.debug.Source
import org.eclipse.lsp4j.debug.SourceBreakpoint
import org.eclipse.lsp4j.debug.StackTraceArguments
import org.eclipse.lsp4j.debug.StepInArguments
import org.eclipse.lsp4j.debug.StepOutArguments
import org.eclipse.lsp4j.debug.StoppedEventArguments
import org.eclipse.lsp4j.debug.TerminateArguments
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

private typealias LineBreakpoint = XLineBreakpoint<RobotCodeLineBreakpointProperties>
private typealias ExceptionBreakpoint = XBreakpoint<RobotCodeExceptionBreakpointProperties>

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
        (it.type as RobotCodeExceptionBreakpointType).filterId
    }
    private val breakpointsMutex = Mutex()
    private var configured = false

    private val editorsProvider = RobotCodeXDebuggerEditorsProvider()
    private val breakpointHandlers = arrayOf(
        RobotCodeLineBreakpointHandler(this),
        RobotCodeExceptionBreakpointHandler(this, RobotCodeUncaughtFailedKeywordsBreakpointType::class.java),
        RobotCodeExceptionBreakpointHandler(this, RobotCodeFailedKeywordsBreakpointType::class.java),
        RobotCodeExceptionBreakpointHandler(this, RobotCodeFailedTestsBreakpointType::class.java),
        RobotCodeExceptionBreakpointHandler(this, RobotCodeFailedSuitesBreakpointType::class.java),
    )

    init {
        session.setPauseActionSupported(true)

        state.configuration = this::sendConfiguration
        debugClient.onStopped.adviseSuspend(Lifetime.Eternal, Dispatchers.IO, this::handleOnStopped)
    }

    private suspend fun createRobotCodeSuspendContext(threadId: Int): RobotCodeSuspendContext {
        return RobotCodeSuspendContext(
            debugServer.stackTrace(StackTraceArguments().apply { this.threadId = threadId }).await(),
            threadId,
            debugServer
        )
    }

    // a stop at a failure applies the matching exception breakpoint; every other stop, and a failure stop without a
    // matching breakpoint, is shown as paused. A stop that the session shows ends Run to Cursor, a failure that the
    // breakpoint passes over does not.
    private suspend fun handleOnStopped(args: StoppedEventArguments) {
        val breakpoint = if (args.reason == "exception") {
            breakpointsMutex.withLock { exceptionBreakpoints.breakpointFor(args.description) }
        } else {
            null
        }
        val context = createRobotCodeSuspendContext(args.threadId)
        if (breakpoint == null) {
            breakpointsMutex.withLock { clearRunToCursorTarget() }
            session.positionReached(context)
        } else if (session.breakpointReached(breakpoint, null, context)) {
            breakpointsMutex.withLock { clearRunToCursorTarget() }
            session.reportMessage(args.text ?: args.description, MessageType.INFO)
        } else {
            debugServer.continue_(ContinueArguments().apply {
                threadId = args.threadId
            }).await()
        }
    }

    override fun getEditorsProvider(): XDebuggerEditorsProvider {
        return editorsProvider
    }

    override fun createConsole(): ExecutionConsole {
        return executionResult.executionConsole
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
                SourceBreakpoint().apply {
                    line = entry.line + 1
                    entry.breakpoint?.let {
                        condition = it.conditionExpression?.expression
                        logMessage = it.logExpressionObject?.expression
                    }
                }
            }.toTypedArray()
        }

        val response = debugServer.setBreakpoints(arguments).await()

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

    override fun stop() {
        runBlocking {
            try {
                debugServer.terminate(TerminateArguments().apply {
                    restart = false
                }).await()
            } catch (_: Exception) { // Ignore may be the server is already terminated
            }
        }
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
