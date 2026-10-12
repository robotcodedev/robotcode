package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.xdebugger.breakpoints.XLineBreakpoint
import com.intellij.xdebugger.breakpoints.XLineBreakpointType
import com.intellij.xdebugger.breakpoints.ui.XBreakpointCustomPropertiesPanel
import com.intellij.xdebugger.evaluation.XDebuggerEditorsProvider
import dev.robotcode.robotcode4ij.RobotResourceFileType
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import dev.robotcode.robotcode4ij.debugging.RobotCodeXDebuggerEditorsProvider

class RobotCodeLineBreakpointType : XLineBreakpointType<RobotCodeLineBreakpointProperties>(ID, NAME) {
    companion object {
        private const val ID = "robotcode-line"
        private const val NAME = "Robot Framework Line Breakpoint"
    }
    
    override fun createBreakpointProperties(file: VirtualFile, line: Int): RobotCodeLineBreakpointProperties? {
        return RobotCodeLineBreakpointProperties()
    }

    // the properties that the project's stored breakpoints are loaded into
    override fun createProperties(): RobotCodeLineBreakpointProperties {
        return RobotCodeLineBreakpointProperties()
    }
    
    override fun canPutAt(file: VirtualFile, line: Int, project: Project): Boolean {
        return file.fileType == RobotSuiteFileType || file.fileType == RobotResourceFileType
    }

    // gives the breakpoint its Condition and "Evaluate and log" fields
    override fun getEditorsProvider(
        breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>, project: Project
    ): XDebuggerEditorsProvider {
        return RobotCodeXDebuggerEditorsProvider()
    }

    override fun createCustomConditionsPanel(): XBreakpointCustomPropertiesPanel<XLineBreakpoint<RobotCodeLineBreakpointProperties>> {
        return RobotCodeHitCountPanel()
    }
}
