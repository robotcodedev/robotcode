package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.breakpoints.XBreakpointProperties

class RobotCodeBreakpointProperties : XBreakpointProperties<RobotCodeBreakpointProperties>() {
    
    override fun getState(): RobotCodeBreakpointProperties {
        return this
    }
    
    override fun loadState(state: RobotCodeBreakpointProperties) {
        TODO("Not yet implemented")
    }
}
