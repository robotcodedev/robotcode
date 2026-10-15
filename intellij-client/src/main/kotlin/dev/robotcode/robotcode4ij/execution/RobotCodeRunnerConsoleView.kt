package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.filters.TextConsoleBuilderFactory
import com.intellij.execution.process.ProcessHandler
import com.intellij.execution.runners.RunContentBuilder
import com.intellij.execution.testframework.TestConsoleProperties
import com.intellij.execution.testframework.sm.runner.ui.SMTRunnerConsoleView
import com.intellij.execution.testframework.ui.TestResultsPanel
import com.intellij.execution.ui.ConsoleView
import com.intellij.execution.ui.ExecutionConsole
import com.intellij.execution.ui.ExecutionConsoleEx
import com.intellij.execution.ui.RunnerLayoutUi
import com.intellij.execution.ui.layout.LayoutAttractionPolicy
import com.intellij.execution.ui.layout.LayoutViewOptions
import com.intellij.execution.ui.layout.PlaceInGrid
import com.intellij.openapi.actionSystem.ActionPlaces
import com.intellij.openapi.actionSystem.DefaultActionGroup
import com.intellij.openapi.util.Disposer
import dev.robotcode.robotcode4ij.RobotCodeBundle

// the id of the "Terminal" content in the window of a run or a debug session
private const val TERMINAL_CONTENT_ID = "RobotCodeTerminal"

/**
 * Adds the [terminal] console as the "Terminal" tab to the window [ui] of a run or a debug session, where the console
 * goes in the tab [tabIndex], unless the window has it already. It is what the user looks at first, so the callers add
 * it before the console, and the window selects it when it starts, instead of the console that a debug session selects.
 */
internal fun addTerminalContent(ui: RunnerLayoutUi, terminal: ConsoleView, tabIndex: Int) {
    if (ui.findContent(TERMINAL_CONTENT_ID) != null) return
    val content = ui.createContent(
        TERMINAL_CONTENT_ID, terminal.component, RobotCodeBundle.message("run.terminal.title"), null,
        terminal.preferredFocusableComponent
    )
    content.isCloseable = false
    // the actions of a console, such as soft wraps and scrolling to the end, as the run's console has them
    content.setActions(
        DefaultActionGroup(*terminal.createConsoleActions()), ActionPlaces.RUNNER_TOOLBAR, terminal.component
    )
    ui.addContent(content, tabIndex, PlaceInGrid.bottom, false)
    // the window keeps one content per condition, so this replaces the console of a debug session
    ui.defaults.initContentAttraction(
        TERMINAL_CONTENT_ID, LayoutViewOptions.STARTUP, LayoutAttractionPolicy.FocusOnce(false)
    )
}

/** Names the platform's console in the window [ui] of a run or a debug session, the results tree, "Debug Console". */
internal fun nameDebugConsole(ui: RunnerLayoutUi) {
    ui.findContent(ExecutionConsole.CONSOLE_CONTENT_ID)?.displayName = RobotCodeBundle.message("run.debugConsole.title")
}

class RobotCodeRunnerConsoleView(consoleProperties: TestConsoleProperties, splitterProperty: String? = null) :
    SMTRunnerConsoleView(consoleProperties, splitterProperty), ExecutionConsoleEx {

    /** The output of the Robot Framework process, as a terminal run shows it. */
    val terminal: ConsoleView = TextConsoleBuilderFactory.getInstance().createBuilder(consoleProperties.project)
        .also { it.setViewer(true) }.console

    init {
        Disposer.register(this, terminal)
    }

    override fun createTestResultsPanel(): TestResultsPanel? {
        return super.createTestResultsPanel()
    }

    override fun initUI() {
        super.initUI()
        // the locations of failures and log messages, and the output files that Robot Framework names become links
        addMessageFilter(RobotCodeConsoleFilter(properties.project))
        terminal.addMessageFilter(RobotCodeConsoleFilter(properties.project))
    }

    override fun attachToProcess(processHandler: ProcessHandler) {
        super.attachToProcess(processHandler)
        terminal.attachToProcess(processHandler)
    }

    // the "Terminal" tab first, then the results with their console as the platform adds them, as the "Debug Console"
    override fun buildUi(layout: RunnerLayoutUi) {
        addTerminalContent(layout, terminal, 0)
        if (layout.findContent(ExecutionConsole.CONSOLE_CONTENT_ID) == null) {
            RunContentBuilder.buildConsoleUiDefault(layout, this)
        }
        nameDebugConsole(layout)
    }

    // the platform remembers the layout of the run window under this id
    override fun getExecutionConsoleId(): String = "RobotCodeRunConsole"

}
