package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.breakpoints.XBreakpointHandler
import com.intellij.xdebugger.breakpoints.XLineBreakpoint

class RobotCodeBreakpointHandler(val process: RobotCodeDebugProcess) :
    XBreakpointHandler<XLineBreakpoint<RobotCodeBreakpointProperties>>(RobotCodeBreakpointType::class.java) {
    override fun registerBreakpoint(breakpoint: XLineBreakpoint<RobotCodeBreakpointProperties>) {
        process.registerBreakpoint(breakpoint)
    }
    
    override fun unregisterBreakpoint(
        breakpoint: XLineBreakpoint<RobotCodeBreakpointProperties>,
        temporary: Boolean
    ) {
        process.unregisterBreakpoint(breakpoint)
    }
}
