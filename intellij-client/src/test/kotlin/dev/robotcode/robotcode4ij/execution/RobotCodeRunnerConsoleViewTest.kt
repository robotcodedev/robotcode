package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.runConfigurationType
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.testframework.sm.SMTestRunnerConnectionUtil
import com.intellij.execution.ui.ExecutionConsole
import com.intellij.execution.ui.RunnerLayoutUi
import com.intellij.openapi.util.Disposer
import com.intellij.testFramework.fixtures.BasePlatformTestCase

class RobotCodeRunnerConsoleViewTest : BasePlatformTestCase() {

    fun testTheRunWindowGetsTheConsoleAndOneTerminalTab() {
        val factory = runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
        val properties = RobotRunnerConsoleProperties(
            RobotCodeRunConfiguration(project, factory), "RobotCode", DefaultRunExecutor.getRunExecutorInstance()
        )
        val console = RobotCodeRunnerConsoleView(properties)
        Disposer.register(testRootDisposable, console)
        SMTestRunnerConnectionUtil.initConsoleView(console, "RobotCode")
        val layout = RunnerLayoutUi.Factory.getInstance(project)
            .create("RobotCode", "RobotCode", "Run", testRootDisposable)

        console.buildUi(layout)
        // a second call, as when a window would be built from the console twice, adds nothing
        console.buildUi(layout)

        // the "Terminal" tab first, then the results tree as the "Debug Console"
        assertEquals(listOf("Terminal", "Debug Console"), layout.contents.map { it.displayName })
        assertEquals("Debug Console", layout.findContent(ExecutionConsole.CONSOLE_CONTENT_ID)!!.displayName)
        assertFalse(layout.findContent("RobotCodeTerminal")!!.isCloseable)
    }
}
