package dev.robotcode.robotcode4ij.lsp

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.redhat.devtools.lsp4ij.server.CannotStartProcessException
import dev.robotcode.robotcode4ij.CheckPythonAndRobotVersionResult
import dev.robotcode.robotcode4ij.RobotCodeHelpers
import org.junit.Assert
import java.nio.file.Path
import java.util.concurrent.atomic.AtomicBoolean

class RobotCodeLanguageServerTest : BasePlatformTestCase() {

    override fun tearDown() {
        try {
            project.putUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY, null)
            project.putUserData(RobotCodeLanguageServerManager.LANGUAGE_SERVER_ENABLED_KEY, null)
            project.langServerManager.allowStart()
        } finally {
            super.tearDown()
        }
    }

    // The environment check stores its result in the project, so a check would leave it there.
    fun testCreatingTheProviderChecksNothingAndStartsNothing() {
        project.putUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY, null)

        val server = RobotCodeLanguageServer(project)

        assertNull(project.getUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY))
        assertNull(server.commandLine)
        assertFalse(server.isAlive)
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

        project.putUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY, CheckPythonAndRobotVersionResult.OK)
        project.langServerManager.allowStart()
        assertTrue(factory.isEnabled(project))
    }

    private fun java(): String {
        return ProcessHandle.current().info().command()
            .orElse(Path.of(System.getProperty("java.home"), "bin", "java").toString())
    }
}
