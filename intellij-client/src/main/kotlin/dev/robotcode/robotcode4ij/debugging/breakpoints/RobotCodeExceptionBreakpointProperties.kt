package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.util.xmlb.XmlSerializerUtil
import com.intellij.xdebugger.breakpoints.XBreakpointProperties

class RobotCodeExceptionBreakpointProperties : XBreakpointProperties<RobotCodeExceptionBreakpointProperties>() {
    // the exception filter of the debugger that the breakpoint stands for; the breakpoint of earlier versions has none
    var kind: String? = null

    override fun getState(): RobotCodeExceptionBreakpointProperties {
        return this
    }

    override fun loadState(state: RobotCodeExceptionBreakpointProperties) {
        XmlSerializerUtil.copyBean(state, this)
    }
}
