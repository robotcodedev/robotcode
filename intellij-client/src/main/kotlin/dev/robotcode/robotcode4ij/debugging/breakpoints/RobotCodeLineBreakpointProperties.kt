package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.xdebugger.breakpoints.XBreakpointProperties

class RobotCodeLineBreakpointProperties : XBreakpointProperties<RobotCodeLineBreakpointProperties>() {
    
    override fun getState(): RobotCodeLineBreakpointProperties {
        return this
    }
    
    override fun loadState(state: RobotCodeLineBreakpointProperties) {
        TODO("Not yet implemented")
    }
}
