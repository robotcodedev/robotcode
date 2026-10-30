package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration

/**
 * The "Run & Debug" values that a run uses, after the defaults of the "Run" and "Debug" pages are applied. [wrapper] is
 * [RobotRunWrapper.PROFILE], [RobotRunWrapper.CUSTOM] with its [wrapperCommand], or [RobotRunWrapper.NONE].
 */
internal data class RunDebugOptions(
    val wrapper: RobotRunWrapper,
    val wrapperCommand: String,
    val robotCodeArguments: String,
    val outputMessages: Boolean,
    val outputLog: Boolean,
    val outputTimestamps: Boolean,
    val attachPython: Boolean,
    val openOutputAfterRun: RobotOpenOutput,
    val stopOnEntry: Boolean,
    val connectionTimeoutSeconds: Int,
    val debuggerArguments: String
)

/**
 * The [configuration]'s "Run & Debug" values for a run, with the defaults of the [project] where the configuration
 * leaves a value to them, as they are when the run starts. A custom wrapper without a command passes none, so the
 * wrapper of the `robot.toml` profile applies, and a connection timeout that is not set is the debugger's default.
 */
internal fun resolveRunDebugOptions(
    project: RobotCodeProjectConfiguration.ProjectState, configuration: RobotCodeRunConfigurationOptions
): RunDebugOptions {
    fun switch(value: RobotRunSwitch, default: Boolean): Boolean {
        return when (value) {
            RobotRunSwitch.INHERIT -> default
            RobotRunSwitch.ON -> true
            RobotRunSwitch.OFF -> false
        }
    }

    val command = when (configuration.wrapper) {
        RobotRunWrapper.INHERIT -> project.debugLaunchWrapper.orEmpty()
        RobotRunWrapper.CUSTOM -> configuration.wrapperCommand.orEmpty()
        RobotRunWrapper.PROFILE, RobotRunWrapper.NONE -> ""
    }
    val wrapper = when {
        configuration.wrapper == RobotRunWrapper.NONE -> RobotRunWrapper.NONE
        command.isBlank() -> RobotRunWrapper.PROFILE
        else -> RobotRunWrapper.CUSTOM
    }
    return RunDebugOptions(
        wrapper = wrapper,
        wrapperCommand = if (wrapper == RobotRunWrapper.CUSTOM) command else "",
        robotCodeArguments = configuration.robotCodeArguments.orEmpty(),
        outputMessages = switch(configuration.outputMessages, project.debugOutputMessages),
        outputLog = switch(configuration.outputLog, project.debugOutputLog),
        outputTimestamps = switch(configuration.outputTimestamps, project.debugOutputTimestamps),
        attachPython = switch(configuration.attachPython, project.debugAttachPython),
        openOutputAfterRun = when (configuration.openOutputAfterRun) {
            RobotRunOpenOutput.INHERIT -> project.runOpenOutputAfterRun
            RobotRunOpenOutput.NONE -> RobotOpenOutput.NONE
            RobotRunOpenOutput.REPORT -> RobotOpenOutput.REPORT
            RobotRunOpenOutput.LOG -> RobotOpenOutput.LOG
        },
        stopOnEntry = configuration.stopOnEntry,
        connectionTimeoutSeconds = configuration.connectionTimeout.takeIf { it > 0 }
            ?: DEBUGGER_CONNECT_TIMEOUT_SECONDS,
        debuggerArguments = configuration.debuggerArguments.orEmpty()
    )
}
