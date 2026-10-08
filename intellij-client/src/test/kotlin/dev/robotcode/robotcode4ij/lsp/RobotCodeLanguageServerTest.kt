package dev.robotcode.robotcode4ij.lsp

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.redhat.devtools.lsp4ij.server.CannotStartProcessException
import dev.robotcode.robotcode4ij.EnvironmentResult
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import org.junit.Assert
import java.nio.file.Path
import java.util.concurrent.atomic.AtomicBoolean

class RobotCodeLanguageServerTest : BasePlatformTestCase() {

    private val environment get() = project.robotCodeEnvironment
    private val usable = EnvironmentState.Checked(EnvironmentResult.Usable)

    override fun setUp() {
        super.setUp()
        environment.resetForTests()
    }

    override fun tearDown() {
        try {
            project.langServerManager.enableForSession()
            project.langServerManager.allowStart()
            environment.resetForTests()
        } finally {
            super.tearDown()
        }
    }

    private fun setProjectState(state: EnvironmentState) {
        environment.checks.setState(environment.projectInterpreter, state)
    }

    fun testCreatingTheProviderChecksNothingAndStartsNothing() {
        val server = RobotCodeLanguageServer(project)

        assertEquals(EnvironmentState.Unknown, environment.projectState)
        assertNull(server.commandLine)
        assertFalse(server.isAlive)
    }

    // LSP4IJ asks on the EDT, for example when a Robot file is opened.
    fun testIsEnabledFollowsTheStateWithoutWaiting() {
        val factory = RobotCodeLanguageServerFactory()
        val states = listOf(
            EnvironmentState.Checking to false,
            usable to true,
            EnvironmentState.Checked(EnvironmentResult.RobotNotInstalled) to false,
            EnvironmentState.Failed("it did not answer within 30 seconds.") to false,
        )
        for ((state, enabled) in states) {
            setProjectState(state)
            val start = System.nanoTime()

            assertEquals(state.toString(), enabled, factory.isEnabled(project))
            // far below the 30 seconds that a check may take
            assertTrue(System.nanoTime() - start < 1_000_000_000)
            assertEquals(state, environment.projectState)
        }
    }

    fun testIsEnabledRequestsACheckWithoutAResult() {
        assertFalse(RobotCodeLanguageServerFactory().isEnabled(project))

        assertTrue(environment.projectState != EnvironmentState.Unknown)
    }

    fun testIsEnabledIsFalseWhileTheStartIsBlocked() {
        setProjectState(usable)
        project.langServerManager.reportStartFailure()

        assertFalse(RobotCodeLanguageServerFactory().isEnabled(project))
    }

    // LSP4IJ stops a server that has not connected yet when the project closes or the server restarts during its start
    // (issue #630).
    fun testStopBeforeTheServerConnected() {
        val server = RobotCodeLanguageServer(project)
        server.stop()
        server.stop()
    }

    // `java -version` exits with code 0 without connecting. The exit code is the error, not an unexpected stop, which
    // LSP4IJ would report instead.
    fun testServerThatExitsBeforeItConnectsFailsTheStart() {
        val server = RobotCodeLanguageServer(project) { GeneralCommandLine(java(), "-version") }
        val unexpectedStop = AtomicBoolean(false)
        server.addUnexpectedServerStopHandler { unexpectedStop.set(true) }

        val error = Assert.assertThrows(CannotStartProcessException::class.java) { server.start() }

        assertTrue(error.message, error.message!!.contains("exit code 0"))
        repeat(50) { if (server.isAlive) Thread.sleep(100) }
        // LSP4IJ calls the handlers when the process handler reports the termination
        Thread.sleep(500)
        assertFalse(unexpectedStop.get())
        server.stop()
        server.stop()
    }

    fun testFailedStartDisablesTheServerUntilTheManagerStartsIt() {
        val server = RobotCodeLanguageServer(project) { GeneralCommandLine(java(), "-version") }
        Assert.assertThrows(CannotStartProcessException::class.java) { server.start() }
        server.stop()
        val factory = RobotCodeLanguageServerFactory()

        assertFalse(factory.isEnabled(project))

        setProjectState(usable)
        project.langServerManager.allowStart()
        assertTrue(factory.isEnabled(project))
    }

    private fun java(): String {
        return ProcessHandle.current().info().command()
            .orElse(Path.of(System.getProperty("java.home"), "bin", "java").toString())
    }
}
