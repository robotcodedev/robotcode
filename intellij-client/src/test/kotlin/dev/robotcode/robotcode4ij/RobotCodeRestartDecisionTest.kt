package dev.robotcode.robotcode4ij

import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration.ProjectState
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettingsMapper
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeRestartDecisionTest {

    private val python = listOf("/opt/py/bin/python", "-u", "-X", "utf8", "/plugin/robotcode")

    // the snapshots of the language server and of the full discovery, built as the plugin builds their command lines
    private fun server(profiles: List<String> = emptyList(), state: ProjectState = ProjectState()) = ServerSnapshot(
        python + robotCodeArguments(emptyList(), "", true, true, profiles, listOf("language-server", "--socket", "<port>")),
        emptyMap(), "/project", RobotCodeServerSettingsMapper.toJsonTree(state).toString(), "{}"
    )

    private fun discovery(extraArgs: List<String> = emptyList(), profiles: List<String> = emptyList()) =
        DiscoverySnapshot(
            python + robotCodeArguments(
                extraArgs, "json", true, true, profiles, listOf("-dp", ".", "discover", "--read-from-stdin", "all")
            ),
            emptyMap(), "/project"
        )

    @Test
    fun headerStyleRestartsOnlyTheServer() {
        val changed = ProjectState().apply { completionHeaderStyle = "*** {name}" }

        assertEquals(
            RestartWork(server = true, discovery = false),
            decideRestart(server(), server(state = changed), discovery(), discovery())
        )
    }

    @Test
    fun robotcodeExtraArgsRunOnlyDiscovery() {
        assertEquals(
            RestartWork(server = false, discovery = true),
            decideRestart(server(), server(), discovery(), discovery(extraArgs = listOf("--log")))
        )
    }

    @Test
    fun profileDoesBoth() {
        assertEquals(
            RestartWork(server = true, discovery = true),
            decideRestart(server(), server(listOf("dev")), discovery(), discovery(profiles = listOf("dev")))
        )
    }

    @Test
    fun identicalSnapshotsDoNothing() {
        assertEquals(RestartWork(server = false, discovery = false), decideRestart(server(), server(), discovery(), discovery()))
    }

    @Test
    fun withoutAServerOrADiscoveryBeforeNothingIsNeeded() {
        val changed = ProjectState().apply { completionHeaderStyle = "*** {name}" }

        assertEquals(
            RestartWork(server = false, discovery = false),
            decideRestart(null, server(state = changed), null, discovery(profiles = listOf("dev")))
        )
        assertEquals(
            RestartWork(server = false, discovery = false),
            decideRestart(server(), null, discovery(), null)
        )
    }
}
