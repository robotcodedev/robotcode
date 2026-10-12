package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.openapi.application.EDT
import com.intellij.openapi.project.Project
import com.intellij.openapi.startup.ProjectActivity
import com.intellij.xdebugger.XDebuggerManager
import com.intellij.xdebugger.XDebuggerUtil
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Removes the project's Robot Framework exception breakpoints whose kind this version does not know, such as one written
 * by hand or by a newer version: the Breakpoints dialog would show it, but the debugger has no filter for it.
 */
class RobotCodeExceptionBreakpointCleanup : ProjectActivity {
    override suspend fun execute(project: Project) {
        if (project.isDefault) return
        val type = XDebuggerUtil.getInstance().findBreakpointType(RobotCodeExceptionBreakpointType::class.java)
        val manager = XDebuggerManager.getInstance(project).breakpointManager
        val unknown = manager.getBreakpoints(type).filter { RobotCodeFailureKind.isUnknown(it.properties) }
        if (unknown.isEmpty()) return
        withContext(Dispatchers.EDT) {
            unknown.forEach { manager.removeBreakpoint(it) }
        }
    }
}
