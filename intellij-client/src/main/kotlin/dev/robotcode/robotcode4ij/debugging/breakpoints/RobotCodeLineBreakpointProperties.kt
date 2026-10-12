package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.util.xmlb.XmlSerializerUtil
import com.intellij.xdebugger.breakpoints.XBreakpointProperties

class RobotCodeLineBreakpointProperties : XBreakpointProperties<RobotCodeLineBreakpointProperties>() {

    // the hit count as the user typed it, in the forms the debugger accepts: `3`, `> 3`, `>= 3`, `< 3`, `<= 3`, `% 3`
    var hitCount: String? = null

    override fun getState(): RobotCodeLineBreakpointProperties {
        return this
    }

    override fun loadState(state: RobotCodeLineBreakpointProperties) {
        XmlSerializerUtil.copyBean(state, this)
    }
}
