package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.frame.XExecutionStack
import com.intellij.xdebugger.frame.XStackFrame
import kotlinx.coroutines.CoroutineScope
import org.eclipse.lsp4j.debug.StackTraceResponse
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

@Suppress("DialogTitleCapitalization") class RobotCodeExecutionStack(
    val stack: StackTraceResponse,
    val debugServer: IDebugProtocolServer,
    scope: CoroutineScope,
    val threadId: Int
) :
    XExecutionStack("Robot Framework Execution Stack") {

    // created once per stop, so that the top frame and the frame list are the same objects
    private val frames = stack.stackFrames.orEmpty().let { frames ->
        frames.mapIndexed { index, frame ->
            RobotCodeStackFrame(frame, debugServer, scope, depth = frames.size - 1 - index, innermost = index == 0)
        }
    }

    override fun getTopFrame(): XStackFrame? {
        return frames.firstOrNull()
    }

    override fun computeStackFrames(
        firstFrameIndex: Int, container: XStackFrameContainer?
    ) {
        container?.addStackFrames(frames.drop(firstFrameIndex), true)
    }
}
