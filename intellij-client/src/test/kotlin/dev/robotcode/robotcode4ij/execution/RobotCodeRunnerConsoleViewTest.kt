package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.runConfigurationType
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.testframework.sm.SMTestRunnerConnectionUtil
import com.intellij.execution.ui.ExecutionConsole
import com.intellij.execution.ui.RunnerLayoutUi
import com.intellij.execution.ui.layout.LayoutAttractionPolicy
import com.intellij.execution.ui.layout.LayoutViewOptions
import com.intellij.openapi.util.Disposer
import com.intellij.openapi.wm.impl.IdeGlassPaneImpl
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.xdebugger.impl.ui.XDebuggerUIConstants
import java.awt.BorderLayout
import javax.swing.JPanel
import javax.swing.JRootPane

class RobotCodeRunnerConsoleViewTest : BasePlatformTestCase() {

    private fun createConsole(): RobotCodeRunnerConsoleView {
        val factory = runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
        val properties = RobotRunnerConsoleProperties(
            RobotCodeRunConfiguration(project, factory), "RobotCode", DefaultRunExecutor.getRunExecutorInstance()
        )
        val console = RobotCodeRunnerConsoleView(properties)
        Disposer.register(testRootDisposable, console)
        SMTestRunnerConnectionUtil.initConsoleView(console, "RobotCode")
        return console
    }

    fun testTheRunWindowGetsTheConsoleAndOneTerminalTab() {
        val console = createConsole()
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

    fun testADebugSessionEndsWithTheTerminalTabSelected() {
        val console = createConsole()
        val layout = RunnerLayoutUi.Factory.getInstance(project)
            .create("RobotCode", "RobotCode", "Debug", testRootDisposable)
        // the attractions of the console in the window of a debug session, as the platform's DebuggerSessionTabBase
        // gives them
        layout.defaults
            .initContentAttraction(
                ExecutionConsole.CONSOLE_CONTENT_ID, LayoutViewOptions.STARTUP, LayoutAttractionPolicy.FocusOnce(false)
            )
            .initContentAttraction(
                ExecutionConsole.CONSOLE_CONTENT_ID, XDebuggerUIConstants.LAYOUT_VIEW_FINISH_CONDITION,
                LayoutAttractionPolicy.FocusOnce()
            )
        console.buildUi(layout)
        // the window brings contents to the front only once it is shown, in a root pane with the platform's glass pane
        val rootPane = JRootPane()
        rootPane.glassPane = IdeGlassPaneImpl(rootPane)
        rootPane.contentPane.add(layout.component)
        val window = JPanel(BorderLayout()).apply { add(rootPane) }
        Disposer.register(testRootDisposable) { window.removeNotify() }
        window.addNotify()
        PlatformTestUtil.dispatchAllInvocationEventsInIdeEventQueue()
        // the user looks at the results tree while the session runs
        layout.selectAndFocus(layout.findContent(ExecutionConsole.CONSOLE_CONTENT_ID)!!, false, false)
        PlatformTestUtil.dispatchAllInvocationEventsInIdeEventQueue()
        assertEquals("Debug Console", layout.contentManager.selectedContent?.displayName)

        // what the platform's window of a debug session does when the session ends
        layout.attractBy(XDebuggerUIConstants.LAYOUT_VIEW_FINISH_CONDITION)
        PlatformTestUtil.dispatchAllInvocationEventsInIdeEventQueue()

        assertEquals("Terminal", layout.contentManager.selectedContent?.displayName)
    }
}
