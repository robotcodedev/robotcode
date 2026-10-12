package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.icons.AllIcons
import com.intellij.ide.util.ChooseElementsDialog
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.xdebugger.XDebuggerManager
import com.intellij.xdebugger.breakpoints.XBreakpoint
import com.intellij.xdebugger.breakpoints.XBreakpointType
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.debugging.FAILED_KEYWORD_FILTER
import dev.robotcode.robotcode4ij.debugging.FAILED_SUITE_FILTER
import dev.robotcode.robotcode4ij.debugging.FAILED_TEST_FILTER
import dev.robotcode.robotcode4ij.debugging.UNCAUGHT_FAILED_KEYWORD_FILTER
import org.jetbrains.annotations.Nls
import org.jetbrains.annotations.NonNls
import javax.swing.Icon
import javax.swing.JComponent

/** A kind of failure that the RobotCode debugger stops at, with the exception filter the debugger knows it by. */
internal enum class RobotCodeFailureKind(val filterId: String) {
    UNCAUGHT_FAILED_KEYWORDS(UNCAUGHT_FAILED_KEYWORD_FILTER),
    FAILED_KEYWORDS(FAILED_KEYWORD_FILTER),
    FAILED_TESTS(FAILED_TEST_FILTER),
    FAILED_SUITES(FAILED_SUITE_FILTER);

    val displayName: @Nls String
        get() = when (this) {
            UNCAUGHT_FAILED_KEYWORDS -> RobotCodeBundle.message("debugger.exceptionBreakpoint.uncaughtFailedKeywords")
            FAILED_KEYWORDS -> RobotCodeBundle.message("debugger.exceptionBreakpoint.failedKeywords")
            FAILED_TESTS -> RobotCodeBundle.message("debugger.exceptionBreakpoint.failedTests")
            FAILED_SUITES -> RobotCodeBundle.message("debugger.exceptionBreakpoint.failedSuites")
        }

    companion object {
        /**
         * The kind of the breakpoint with [properties]. The exception breakpoint of earlier versions has no kind; it stops
         * at uncaught keyword failures.
         */
        fun of(properties: RobotCodeExceptionBreakpointProperties?): RobotCodeFailureKind {
            return entries.firstOrNull { it.filterId == properties?.kind } ?: UNCAUGHT_FAILED_KEYWORDS
        }

        /** Whether [properties] name a kind this version does not know, as one written by hand or by a newer version. */
        fun isUnknown(properties: RobotCodeExceptionBreakpointProperties?): Boolean {
            val kind = properties?.kind ?: return false
            return entries.none { it.filterId == kind }
        }
    }
}

/** The kinds the user can add next to "Uncaught Failed Keywords", the default breakpoint, without those in [present]. */
internal fun missingKinds(present: Collection<RobotCodeFailureKind>): List<RobotCodeFailureKind> {
    return RobotCodeFailureKind.entries.filter { it != RobotCodeFailureKind.UNCAUGHT_FAILED_KEYWORDS && it !in present }
}

/**
 * The Robot Framework exception breakpoints, one group in the Breakpoints dialog: "Uncaught Failed Keywords" as the
 * default breakpoint, and the kinds of failure the user adds.
 */
class RobotCodeExceptionBreakpointType :
    XBreakpointType<XBreakpoint<RobotCodeExceptionBreakpointProperties>, RobotCodeExceptionBreakpointProperties>(
        // the id of the former "Any Exception" breakpoint, so that its stored state carries over to the default breakpoint
        "robotcode-exception", RobotCodeBundle.message("debugger.exceptionBreakpoint.title")
    ) {

    override fun getDisplayText(breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>): @Nls String {
        return RobotCodeFailureKind.of(breakpoint.properties).displayName
    }

    override fun getEnabledIcon(): Icon {
        return AllIcons.Debugger.Db_exception_breakpoint
    }

    override fun getDisabledIcon(): Icon {
        return AllIcons.Debugger.Db_disabled_exception_breakpoint
    }

    override fun createProperties(): RobotCodeExceptionBreakpointProperties {
        return RobotCodeExceptionBreakpointProperties()
    }

    override fun getBreakpointsDialogHelpTopic(): @NonNls String {
        return "reference.dialogs.breakpoints"
    }

    override fun createDefaultBreakpoint(
        creator: XBreakpointCreator<RobotCodeExceptionBreakpointProperties?>
    ): XBreakpoint<RobotCodeExceptionBreakpointProperties?> {
        val properties = RobotCodeExceptionBreakpointProperties().apply {
            kind = RobotCodeFailureKind.UNCAUGHT_FAILED_KEYWORDS.filterId
        }
        return creator.createBreakpoint(properties).apply { isEnabled = true }
    }

    override fun isAddBreakpointButtonVisible(): Boolean {
        return true
    }

    // asks for the kinds the project does not have yet; the Breakpoints dialog selects the breakpoint this returns
    override fun addBreakpoint(
        project: Project, parentComponent: JComponent?
    ): XBreakpoint<RobotCodeExceptionBreakpointProperties>? {
        val manager = XDebuggerManager.getInstance(project).breakpointManager
        val missing = missingKinds(manager.getBreakpoints(this).map { RobotCodeFailureKind.of(it.properties) })
        if (missing.isEmpty()) {
            Messages.showInfoMessage(project, RobotCodeBundle.message("debugger.exceptionBreakpoint.allAdded"), title)
            return null
        }
        val chosen = object : ChooseElementsDialog<RobotCodeFailureKind>(
            project, missing, title, RobotCodeBundle.message("debugger.exceptionBreakpoint.chooseKinds"), false
        ) {
            override fun getItemText(item: RobotCodeFailureKind): String = item.displayName
            override fun getItemIcon(item: RobotCodeFailureKind): Icon = AllIcons.Debugger.Db_exception_breakpoint
        }.showAndGetResult()
        return chosen.map { kind ->
            manager.addBreakpoint(this, RobotCodeExceptionBreakpointProperties().apply { this.kind = kind.filterId })
        }.firstOrNull()
    }
}
