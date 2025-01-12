package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.frame.XExecutionStack
import com.intellij.xdebugger.frame.XSuspendContext
import org.eclipse.lsp4j.debug.StackTraceResponse
import org.eclipse.lsp4j.debug.Variable
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

class RobotCodeSuspendContext(
    val stack: StackTraceResponse,
    val threadId: Int,
    val debugServer: IDebugProtocolServer,
    val session: XDebugSession
) : XSuspendContext() {
    
    val variablesCache: MutableMap<Pair<Int?, String>, Variable> = mutableMapOf()
    
    override fun getExecutionStacks(): Array<XExecutionStack> {
        return arrayOf(RobotCodeExecutionStack(stack, debugServer, threadId, session))
    }
    
    override fun getActiveExecutionStack(): XExecutionStack {
        return RobotCodeExecutionStack(stack, debugServer, threadId, session)
    }
}
