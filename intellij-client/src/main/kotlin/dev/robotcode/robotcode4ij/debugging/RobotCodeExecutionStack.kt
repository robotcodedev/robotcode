package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.frame.XExecutionStack
import com.intellij.xdebugger.frame.XStackFrame
import org.eclipse.lsp4j.debug.StackTraceResponse
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

@Suppress("DialogTitleCapitalization") class RobotCodeExecutionStack(
    val stack: StackTraceResponse,
    val debugServer: IDebugProtocolServer,
    val threadId: Int,
    val session: XDebugSession
) :
    XExecutionStack("Robot Framework Execution Stack") {
    override fun getTopFrame(): XStackFrame? {
        return stack.stackFrames.firstOrNull()?.let {
            RobotCodeStackFrame(
                it,
                debugServer,
                session
            )
        }
    }
    
    override fun computeStackFrames(
        firstFrameIndex: Int, container: XStackFrameContainer?
    ) {
        container?.addStackFrames(stack.stackFrames.drop(firstFrameIndex).map {
            RobotCodeStackFrame(
                it,
                debugServer,
                session
            )
        }, true)
    }
    
}
