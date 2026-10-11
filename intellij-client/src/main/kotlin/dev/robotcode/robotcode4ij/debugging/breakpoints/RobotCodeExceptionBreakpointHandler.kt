package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.xdebugger.breakpoints.XBreakpoint
import com.intellij.xdebugger.breakpoints.XBreakpointHandler
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProcess

class RobotCodeExceptionBreakpointHandler(
    val process: RobotCodeDebugProcess, type: Class<out RobotCodeExceptionBreakpointType>
) : XBreakpointHandler<XBreakpoint<RobotCodeExceptionBreakpointProperties>>(type) {
    override fun registerBreakpoint(breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>) {
        process.registerExceptionBreakpoint(breakpoint)
    }

    override fun unregisterBreakpoint(
        breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>, temporary: Boolean
    ) {
        process.unregisterExceptionBreakpoint(breakpoint)
    }

}
