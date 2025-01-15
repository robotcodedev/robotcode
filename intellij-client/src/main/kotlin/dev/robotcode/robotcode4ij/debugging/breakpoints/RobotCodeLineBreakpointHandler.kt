package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.xdebugger.breakpoints.XBreakpointHandler
import com.intellij.xdebugger.breakpoints.XLineBreakpoint
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProcess

class RobotCodeLineBreakpointHandler(val process: RobotCodeDebugProcess) :
    XBreakpointHandler<XLineBreakpoint<RobotCodeLineBreakpointProperties>>(RobotCodeLineBreakpointType::class.java) {
    override fun registerBreakpoint(breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>) {
        process.registerBreakpoint(breakpoint)
    }
    
    override fun unregisterBreakpoint(
        breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>,
        temporary: Boolean
    ) {
        process.unregisterBreakpoint(breakpoint)
    }
}
