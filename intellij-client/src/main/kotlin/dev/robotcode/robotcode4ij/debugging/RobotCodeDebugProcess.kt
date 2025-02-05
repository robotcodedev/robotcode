package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.ExecutionResult
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.ui.ExecutionConsole
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
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeLineBreakpointHandler
import dev.robotcode.robotcode4ij.debugging.breakpoints.RobotCodeLineBreakpointProperties
import dev.robotcode.robotcode4ij.execution.RobotCodeRunProfileState
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
    
    init {
        session.setPauseActionSupported(true)
        
        state.afterInitialize.adviseSuspend(Lifetime.Eternal, Dispatchers.IO) { sendBreakpointRequest() }
        debugClient.onStopped.adviseSuspend(Lifetime.Eternal, Dispatchers.IO, this::handleOnStopped)
    }
    
    private suspend fun createRobotCodeSuspendContext(threadId: Int): RobotCodeSuspendContext {
        return RobotCodeSuspendContext(
            debugServer.stackTrace(StackTraceArguments().apply { this.threadId = threadId }).await(),
            threadId,
            debugServer,
            session
        )
    }
    
    private suspend fun handleOnStopped(args: StoppedEventArguments) {
        when (args.reason) {
            "breakpoint" -> {
                val bp = breakpoints.firstOrNull { it.id != null && it.id in args.hitBreakpointIds }
                
                if (bp is LineBreakpointInfo) {
                    if (!session.breakpointReached(
                            bp.breakpoint, null, createRobotCodeSuspendContext(
                                args.threadId
                            )
                        )
                    ) {
                        debugServer.continue_(ContinueArguments().apply {
                            threadId = args.threadId
                        }).await()
                    }
                } else {
                    session.positionReached(createRobotCodeSuspendContext(args.threadId))
                }
            }
            
            "exception" -> {
                if (!session.breakpointReached(
                        exceptionBreakpoints.first().breakpoint,
                        null,
                        createRobotCodeSuspendContext(args.threadId)
                    )
                ) {
                    debugServer.continue_(ContinueArguments().apply {
                        threadId = args.threadId
                    }).await()
                }
            }
            
            else -> {
                session.positionReached(createRobotCodeSuspendContext(args.threadId))
            }
        }
        removeCurrentOneTimeBreakpoint()
    }
    
    private open class BreakPointInfo(val line: Int, var file: VirtualFile, var id: Int? = null)
    private class LineBreakpointInfo(
        val breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>, id: Int? = null
    ) : BreakPointInfo(breakpoint.line, breakpoint.sourcePosition!!.file, id)
    
    private class ExceptionBreakpointInfo(
        val breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>, id: Int? = null
    )
    
    private class OneTimeBreakpointInfo(val position: XSourcePosition, id: Int? = null) :
        BreakPointInfo(position.line, position.file, id)
    
    private val exceptionBreakpoints = mutableListOf<ExceptionBreakpointInfo>()
    
    private val breakpoints = mutableListOf<BreakPointInfo>()
    private val breakpointMap = mutableMapOf<VirtualFile, MutableMap<Int, BreakPointInfo>>()
    private val breakpointsMapMutex = Mutex()
    
    private val editorsProvider = RobotCodeXDebuggerEditorsProvider()
    private val breakpointHandler = RobotCodeLineBreakpointHandler(this)
    private val exceptionBreakpointHandler = RobotCodeExceptionBreakpointHandler(this)
    
    override fun getEditorsProvider(): XDebuggerEditorsProvider {
        return editorsProvider
    }
    
    override fun createConsole(): ExecutionConsole {
        return executionResult.executionConsole
    }
    
    override fun doGetProcessHandler(): ProcessHandler? {
        return executionResult.processHandler
    }
    
    override fun sessionInitialized() {
        super.sessionInitialized()
    }
    
    override fun getBreakpointHandlers(): Array<out XBreakpointHandler<*>?> {
        return arrayOf(breakpointHandler, exceptionBreakpointHandler)
    }
    
    fun registerExceptionBreakpoint(breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>) {
        runBlocking {
            breakpointsMapMutex.withLock {
                exceptionBreakpoints.add(ExceptionBreakpointInfo(breakpoint))
            }
        }
    }
    
    fun unregisterExceptionBreakpoint(breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>) {
        runBlocking {
            breakpointsMapMutex.withLock {
                exceptionBreakpoints.removeIf { it.breakpoint == breakpoint }
            }
        }
    }
    
    fun registerBreakpoint(breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>) {
        runBlocking {
            breakpointsMapMutex.withLock {
                breakpoint.sourcePosition?.let {
                    if (!breakpointMap.containsKey(it.file)) {
                        breakpointMap[it.file] = mutableMapOf()
                    }
                    val bpMap = breakpointMap[it.file]!!
                    bpMap[breakpoint.line] = LineBreakpointInfo(breakpoint)
                    
                    sendBreakpointRequest(it.file)
                }
            }
        }
    }
    
    fun unregisterBreakpoint(breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>) {
        runBlocking {
            breakpointsMapMutex.withLock {
                breakpoint.sourcePosition?.let {
                    if (breakpointMap.containsKey(it.file)) {
                        val bpMap = breakpointMap[it.file]!!
                        bpMap.remove(breakpoint.line)
                        
                        sendBreakpointRequest(it.file)
                    }
                }
            }
        }
    }
    
    private suspend fun sendBreakpointRequest() {
        if (!state.isInitialized) return
        
        for (file in breakpointMap.keys) {
            sendBreakpointRequest(file)
        }
    }
    
    private suspend fun sendBreakpointRequest(file: VirtualFile) {
        if (!state.isInitialized) {
            return
        }
        
        val breakpoints = breakpointMap[file]!!.entries
        if (breakpoints.isEmpty()) {
            return
        }
        val arguments = SetBreakpointsArguments()
        val source = Source()
        source.path = file.toNioPath().toString()
        arguments.source = source
        
        val dapBreakpoints = breakpoints.map {
            val bp = it.value
            SourceBreakpoint().apply {
                line = bp.line + 1
                if (bp is LineBreakpointInfo) {
                    condition = bp.breakpoint.conditionExpression?.expression
                    logMessage = bp.breakpoint.logExpressionObject?.expression
                }
            }
        }
        
        arguments.breakpoints = dapBreakpoints.toTypedArray()
        
        val response = debugServer.setBreakpoints(arguments).await()
        
        breakpoints.forEach {
            val responseBreakpoint = response.breakpoints.firstOrNull { x -> x.line - 1 == it.value.line }
            if (responseBreakpoint != null) {
                it.value.id = responseBreakpoint.id
                
                (it.value as? LineBreakpointInfo)?.let { lineBreakpointInfo ->
                    if (responseBreakpoint.isVerified == true) {
                        session.setBreakpointVerified(lineBreakpointInfo.breakpoint)
                    } else {
                        session.setBreakpointInvalid(lineBreakpointInfo.breakpoint, "Invalid breakpoint")
                    }
                }
            }
        }
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
    
    private var _oneTimeBreakpointInfo: OneTimeBreakpointInfo? = null
    
    private suspend fun removeCurrentOneTimeBreakpoint() {
        _oneTimeBreakpointInfo?.let {
            _oneTimeBreakpointInfo = null
            breakpointMap[it.file]?.remove(it.line)
            sendBreakpointRequest(it.file)
        }
    }
    
    override fun runToPosition(position: XSourcePosition, context: XSuspendContext?) {
        runBlocking {
            
            if (!breakpointMap.containsKey(position.file)) {
                breakpointMap[position.file] = mutableMapOf()
            }
            val bpMap = breakpointMap[position.file]!!
            
            removeCurrentOneTimeBreakpoint()
            
            if (bpMap.containsKey(position.line)) {
                return@runBlocking
            }
            
            _oneTimeBreakpointInfo = OneTimeBreakpointInfo(position)
            bpMap[position.line] = OneTimeBreakpointInfo(position)
            
            sendBreakpointRequest(position.file)
            
            resume(context)
        }
    }
    
    override fun startPausing() {
        runBlocking {
            debugServer.pause(PauseArguments().apply { threadId = 0 }).await()
        }
    }
}
