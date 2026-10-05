package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.xdebugger.breakpoints.XLineBreakpointType
import dev.robotcode.robotcode4ij.RobotResourceFileType
import dev.robotcode.robotcode4ij.RobotSuiteFileType

class RobotCodeLineBreakpointType : XLineBreakpointType<RobotCodeLineBreakpointProperties>(ID, NAME) {
    companion object {
        private const val ID = "robotcode-line"
        private const val NAME = "Robot Framework Line Breakpoint"
    }
    
    override fun createBreakpointProperties(file: VirtualFile, line: Int): RobotCodeLineBreakpointProperties? {
        return RobotCodeLineBreakpointProperties()
    }
    
    override fun canPutAt(file: VirtualFile, line: Int, project: Project): Boolean {
        return file.fileType == RobotSuiteFileType || file.fileType == RobotResourceFileType
    }
}
