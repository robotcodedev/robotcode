package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.xdebugger.breakpoints.XBreakpoint
import com.intellij.xdebugger.breakpoints.XBreakpointHandler
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProcess

class RobotCodeExceptionBreakpointHandler(val process: RobotCodeDebugProcess) :
    XBreakpointHandler<XBreakpoint<RobotCodeExceptionBreakpointProperties>>(RobotCodeExceptionBreakpointType::class.java) {
    override fun registerBreakpoint(breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>) {
        process.registerExceptionBreakpoint(breakpoint)
    }
    
    override fun unregisterBreakpoint(
        breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>, temporary: Boolean
    ) {
        process.unregisterExceptionBreakpoint(breakpoint)
    }
    
}
