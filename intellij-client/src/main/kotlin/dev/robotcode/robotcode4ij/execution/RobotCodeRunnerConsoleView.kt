package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.testframework.TestConsoleProperties
import com.intellij.execution.testframework.sm.runner.ui.SMTRunnerConsoleView
import com.intellij.execution.testframework.ui.TestResultsPanel

class RobotCodeRunnerConsoleView(consoleProperties: TestConsoleProperties, splitterProperty: String? = null) :
    SMTRunnerConsoleView(consoleProperties, splitterProperty) {
    
    override fun createTestResultsPanel(): TestResultsPanel? {
        return super.createTestResultsPanel()
    }
    
    override fun initUI() {
        super.initUI()
    }
    
}
