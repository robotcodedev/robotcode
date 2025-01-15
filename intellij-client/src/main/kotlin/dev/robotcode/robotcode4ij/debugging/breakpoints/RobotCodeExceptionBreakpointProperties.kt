package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.xdebugger.breakpoints.XBreakpointProperties

class RobotCodeExceptionBreakpointProperties : XBreakpointProperties<RobotCodeExceptionBreakpointProperties>() {
    override fun getState(): RobotCodeExceptionBreakpointProperties? {
        return this
    }
    
    override fun loadState(state: RobotCodeExceptionBreakpointProperties) {
        TODO("Not yet implemented")
    }
}
