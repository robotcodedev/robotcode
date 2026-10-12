package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.frame.XExecutionStack
import com.intellij.xdebugger.frame.XSuspendContext
import org.eclipse.lsp4j.debug.StackTraceResponse
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

class RobotCodeSuspendContext(
    val stack: StackTraceResponse,
    val threadId: Int,
    val debugServer: IDebugProtocolServer
) : XSuspendContext() {

    // created once per stop, together with its frames
    private val executionStack = RobotCodeExecutionStack(stack, debugServer, threadId)

    override fun getExecutionStacks(): Array<XExecutionStack> {
        return arrayOf(executionStack)
    }

    override fun getActiveExecutionStack(): XExecutionStack {
        return executionStack
    }
}
