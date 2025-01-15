package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.icons.AllIcons
import com.intellij.openapi.project.Project
import com.intellij.xdebugger.breakpoints.XBreakpoint
import com.intellij.xdebugger.breakpoints.XBreakpointType
import org.jetbrains.annotations.Nls
import org.jetbrains.annotations.NonNls
import javax.swing.Icon
import javax.swing.JComponent

class RobotCodeExceptionBreakpointType :
    XBreakpointType<XBreakpoint<RobotCodeExceptionBreakpointProperties>, RobotCodeExceptionBreakpointProperties>(
        ID,
        NAME
    ) {
    
    companion object {
        private const val ID = "robotcode-exception"
        private const val NAME = "Robot Framework Exception Breakpoint"
    }
    
    override fun getDisplayText(breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>): @Nls String? {
        return "Any Exception"
    }
    
    override fun getEnabledIcon(): Icon {
        return AllIcons.Debugger.Db_exception_breakpoint
    }
    
    override fun getDisabledIcon(): Icon {
        return AllIcons.Debugger.Db_disabled_exception_breakpoint
    }
    
    override fun createProperties(): RobotCodeExceptionBreakpointProperties? {
        return RobotCodeExceptionBreakpointProperties()
    }
    
    override fun addBreakpoint(
        project: Project?,
        parentComponent: JComponent?
    ): XBreakpoint<RobotCodeExceptionBreakpointProperties>? {
        return super.addBreakpoint(project, parentComponent)
    }
    
    override fun getBreakpointsDialogHelpTopic(): @NonNls String? {
        return "reference.dialogs.breakpoints"
    }
    
    override fun createDefaultBreakpoint(creator: XBreakpointCreator<RobotCodeExceptionBreakpointProperties?>): XBreakpoint<RobotCodeExceptionBreakpointProperties?>? {
        var breakpoint = creator.createBreakpoint(RobotCodeExceptionBreakpointProperties())
        breakpoint.isEnabled = true
        return breakpoint
    }
    
}
