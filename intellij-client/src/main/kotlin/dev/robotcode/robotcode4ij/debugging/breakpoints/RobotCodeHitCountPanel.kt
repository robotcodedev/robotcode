package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.openapi.project.ProjectManager
import com.intellij.ui.components.JBTextField
import com.intellij.ui.dsl.builder.panel
import com.intellij.xdebugger.XDebuggerManager
import com.intellij.xdebugger.breakpoints.XLineBreakpoint
import com.intellij.xdebugger.breakpoints.ui.XBreakpointCustomPropertiesPanel
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.debugging.RobotCodeDebugProcess
import javax.swing.JComponent

/** The hit count of a Robot Framework line breakpoint, with a note on what its log text means with and without Suspend. */
class RobotCodeHitCountPanel : XBreakpointCustomPropertiesPanel<XLineBreakpoint<RobotCodeLineBreakpointProperties>>() {
    private val hitCount = JBTextField(10).apply {
        emptyText.text = RobotCodeBundle.message("debugger.lineBreakpoint.hitCount.empty")
    }

    private val component = panel {
        row(RobotCodeBundle.message("debugger.lineBreakpoint.hitCount")) {
            cell(hitCount)
        }
        row {
            comment(RobotCodeBundle.message("debugger.lineBreakpoint.logComment"))
        }
    }

    override fun getComponent(): JComponent = component

    override fun isVisibleOnPopup(breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>): Boolean = true

    override fun loadFrom(breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>) {
        hitCount.text = breakpoint.properties.hitCount.orEmpty()
    }

    override fun saveTo(breakpoint: XLineBreakpoint<RobotCodeLineBreakpointProperties>) {
        val value = hitCount.text.trim().ifEmpty { null }
        if (breakpoint.properties.hitCount == value) return
        breakpoint.properties.hitCount = value
        // the IDE reports no change of these properties, so running debug sessions get the new hit count from here
        for (project in ProjectManager.getInstance().openProjects) {
            for (session in XDebuggerManager.getInstance(project).debugSessions) {
                (session.debugProcess as? RobotCodeDebugProcess)?.breakpointPropertiesChanged(breakpoint)
            }
        }
    }
}
