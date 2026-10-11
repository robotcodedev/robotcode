package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.icons.AllIcons
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

/** The Robot Framework exception breakpoint for one exception filter of the RobotCode debugger. */
abstract class RobotCodeExceptionBreakpointType(
    id: String,
    private val name: @Nls String,
    val filterId: String,
    private val enabledByDefault: Boolean,
) : XBreakpointType<XBreakpoint<RobotCodeExceptionBreakpointProperties>, RobotCodeExceptionBreakpointProperties>(
    id, RobotCodeBundle.message("debugger.exceptionBreakpoint.title", name)
) {

    override fun getDisplayText(breakpoint: XBreakpoint<RobotCodeExceptionBreakpointProperties>): @Nls String {
        return name
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
        return creator.createBreakpoint(RobotCodeExceptionBreakpointProperties()).apply { isEnabled = enabledByDefault }
    }
}

// keeps the id of the former "Any Exception" breakpoint, which always stopped at uncaught keyword failures, so that its
// stored state carries over
class RobotCodeUncaughtFailedKeywordsBreakpointType : RobotCodeExceptionBreakpointType(
    "robotcode-exception",
    RobotCodeBundle.message("debugger.exceptionBreakpoint.uncaughtFailedKeywords"),
    UNCAUGHT_FAILED_KEYWORD_FILTER,
    enabledByDefault = true,
)

class RobotCodeFailedKeywordsBreakpointType : RobotCodeExceptionBreakpointType(
    "robotcode-failed-keyword",
    RobotCodeBundle.message("debugger.exceptionBreakpoint.failedKeywords"),
    FAILED_KEYWORD_FILTER,
    enabledByDefault = false,
)

class RobotCodeFailedTestsBreakpointType : RobotCodeExceptionBreakpointType(
    "robotcode-failed-test",
    RobotCodeBundle.message("debugger.exceptionBreakpoint.failedTests"),
    FAILED_TEST_FILTER,
    enabledByDefault = false,
)

class RobotCodeFailedSuitesBreakpointType : RobotCodeExceptionBreakpointType(
    "robotcode-failed-suite",
    RobotCodeBundle.message("debugger.exceptionBreakpoint.failedSuites"),
    FAILED_SUITE_FILTER,
    enabledByDefault = false,
)
