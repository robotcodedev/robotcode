package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.DefaultExecutionResult
import com.intellij.execution.process.NopProcessHandler
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.ui.ConsoleView
import org.junit.Assert.assertSame
import org.junit.Test
import java.lang.reflect.Proxy

class RobotCodePythonDebugRunnerTest {

    // PyCharm switches the Python debug console to its prompt only while the console's process runs
    @Test
    fun thePythonDebugConsoleIsAttachedToThePythonSession() {
        var attached: ProcessHandler? = null
        val console = Proxy.newProxyInstance(javaClass.classLoader, arrayOf(ConsoleView::class.java)) { _, method, args ->
            if (method.name == "attachToProcess") attached = args[0] as ProcessHandler
            null
        } as ConsoleView
        val run = NopProcessHandler()
        var handed: ProcessHandler? = null

        val python = pythonSessionHandler(DefaultExecutionResult(console, run)) { handed = it }

        assertSame(run, handed)
        assertSame(python, attached)
    }
}
