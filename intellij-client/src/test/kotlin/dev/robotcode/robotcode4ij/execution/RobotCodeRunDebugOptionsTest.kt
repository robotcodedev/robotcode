package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The "Run & Debug" values of a new configuration in a project without settings: VS Code's defaults. */
internal val defaultRunDebugOptions =
    resolveRunDebugOptions(RobotCodeProjectConfiguration.ProjectState(), RobotCodeRunConfigurationOptions())

class RobotCodeRunDebugOptionsTest {

    private fun project(values: RobotCodeProjectConfiguration.ProjectState.() -> Unit = {}) =
        RobotCodeProjectConfiguration.ProjectState().apply(values)

    private fun configuration(values: RobotCodeRunConfigurationOptions.() -> Unit = {}) =
        RobotCodeRunConfigurationOptions().apply(values)

    // every project default differs from VS Code's
    private val changedProject = project {
        debugLaunchWrapper = "xvfb-run -a"
        debugOutputMessages = true
        debugOutputLog = false
        debugOutputTimestamps = true
        debugAttachPython = true
        runOpenOutputAfterRun = RobotOpenOutput.REPORT
    }

    @Test
    fun aNewConfigurationInAProjectWithoutSettingsGetsTheDefaultsOfVSCode() {
        assertEquals(
            RunDebugOptions(
                RobotRunWrapper.PROFILE, "", "", outputMessages = false, outputLog = true, outputTimestamps = false,
                attachPython = false, openOutputAfterRun = RobotOpenOutput.NONE, stopOnEntry = false,
                connectionTimeoutSeconds = 15, debuggerArguments = ""
            ),
            resolveRunDebugOptions(project(), configuration())
        )
    }

    @Test
    fun valuesLeftToTheProjectTakeItsDefaults() {
        assertEquals(
            RunDebugOptions(
                RobotRunWrapper.CUSTOM, "xvfb-run -a", "", outputMessages = true, outputLog = false,
                outputTimestamps = true, attachPython = true, openOutputAfterRun = RobotOpenOutput.REPORT,
                stopOnEntry = false, connectionTimeoutSeconds = 15, debuggerArguments = ""
            ),
            resolveRunDebugOptions(changedProject, configuration())
        )
    }

    @Test
    fun valuesSetInTheConfigurationWinOverTheProjectDefaults() {
        val configuration = configuration {
            wrapper = RobotRunWrapper.NONE
            robotCodeArguments = "--verbose"
            outputMessages = RobotRunSwitch.OFF
            outputLog = RobotRunSwitch.ON
            outputTimestamps = RobotRunSwitch.OFF
            attachPython = RobotRunSwitch.OFF
            openOutputAfterRun = RobotRunOpenOutput.LOG
            stopOnEntry = true
            connectionTimeout = 30
            debuggerArguments = "--group-output"
        }

        assertEquals(
            RunDebugOptions(
                RobotRunWrapper.NONE, "", "--verbose", outputMessages = false, outputLog = true,
                outputTimestamps = false, attachPython = false, openOutputAfterRun = RobotOpenOutput.LOG,
                stopOnEntry = true, connectionTimeoutSeconds = 30, debuggerArguments = "--group-output"
            ),
            resolveRunDebugOptions(changedProject, configuration)
        )
    }

    @Test
    fun eachWrapperChoice() {
        // the project's launch wrapper, the configuration's choice and command, the wrapper the run gets
        val cases = listOf(
            listOf("", RobotRunWrapper.INHERIT, null, RobotRunWrapper.PROFILE, ""),
            listOf("xvfb-run -a", RobotRunWrapper.INHERIT, null, RobotRunWrapper.CUSTOM, "xvfb-run -a"),
            listOf("xvfb-run -a", RobotRunWrapper.PROFILE, null, RobotRunWrapper.PROFILE, ""),
            listOf("xvfb-run -a", RobotRunWrapper.CUSTOM, "my-wrapper --", RobotRunWrapper.CUSTOM, "my-wrapper --"),
            listOf("xvfb-run -a", RobotRunWrapper.CUSTOM, "  ", RobotRunWrapper.PROFILE, ""),
            listOf("xvfb-run -a", RobotRunWrapper.NONE, null, RobotRunWrapper.NONE, "")
        )
        for ((projectWrapper, choice, command, expected, expectedCommand) in cases) {
            val options = resolveRunDebugOptions(
                project { debugLaunchWrapper = projectWrapper as String },
                configuration {
                    wrapper = choice as RobotRunWrapper
                    wrapperCommand = command as String?
                }
            )

            assertEquals(
                "$choice with $command", expected to expectedCommand, options.wrapper to options.wrapperCommand
            )
        }
    }

    @Test
    fun aChangedProjectDefaultReachesAnUnchangedConfiguration() {
        val project = project()
        val configuration = configuration()
        assertFalse(resolveRunDebugOptions(project, configuration).outputTimestamps)

        project.debugOutputTimestamps = true

        assertTrue(resolveRunDebugOptions(project, configuration).outputTimestamps)
    }

    @Test
    fun attachPythonFollowsTheProjectDefaultUnlessTheConfigurationSetsIt() {
        // the project default, the configuration's switch, the value the run gets
        val cases = listOf(
            Triple(false, RobotRunSwitch.INHERIT, false),
            Triple(true, RobotRunSwitch.INHERIT, true),
            Triple(false, RobotRunSwitch.ON, true),
            Triple(true, RobotRunSwitch.OFF, false)
        )
        for ((projectDefault, switch, expected) in cases) {
            val options = resolveRunDebugOptions(
                project { debugAttachPython = projectDefault }, configuration { attachPython = switch }
            )

            assertEquals("$switch with the project default $projectDefault", expected, options.attachPython)
        }
    }

    @Test
    fun aConnectionTimeoutThatIsNotSetIsTheDebuggersDefault() {
        fun timeoutOf(seconds: Int) =
            resolveRunDebugOptions(project(), configuration { connectionTimeout = seconds }).connectionTimeoutSeconds

        assertEquals(15, timeoutOf(0))
        assertEquals(30, timeoutOf(30))
    }
}
