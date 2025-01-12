package dev.robotcode.robotcode4ij.debugging

import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.xdebugger.breakpoints.XLineBreakpointType

class RobotCodeBreakpointType : XLineBreakpointType<RobotCodeBreakpointProperties>(ID, NAME) {
    companion object {
        private const val ID = "robotcode-line"
        private const val NAME = "robotcode-line-breakpoint"
    }
    
    override fun createBreakpointProperties(file: VirtualFile, line: Int): RobotCodeBreakpointProperties? {
        return RobotCodeBreakpointProperties()
    }
    
    override fun canPutAt(file: VirtualFile, line: Int, project: Project): Boolean {
        return true
    }
}
