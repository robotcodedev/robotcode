package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.xdebugger.breakpoints.XBreakpointProperties

class RobotCodeExceptionBreakpointProperties : XBreakpointProperties<RobotCodeExceptionBreakpointProperties>() {
    override fun getState(): RobotCodeExceptionBreakpointProperties? {
        return this
    }
    
    // the properties have no fields, so a stored state has nothing to load
    override fun loadState(state: RobotCodeExceptionBreakpointProperties) {}
}
