package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.Location
import com.intellij.execution.testframework.TestConsoleProperties
import com.intellij.execution.testframework.actions.AbstractRerunFailedTestsAction
import com.intellij.execution.testframework.sm.SMCustomMessagesParsing
import com.intellij.execution.testframework.sm.runner.OutputToGeneralTestEventsConverter
import com.intellij.execution.testframework.sm.runner.SMTRunnerConsoleProperties
import com.intellij.execution.testframework.sm.runner.SMTestLocator
import com.intellij.execution.testframework.sm.runner.ui.SMTRunnerConsoleView
import com.intellij.execution.ui.ConsoleView
import com.intellij.pom.Navigatable

class RobotRunnerConsoleProperties(
    private val config: RobotCodeRunConfiguration, testFrameworkName: String, executor: Executor
) : SMTRunnerConsoleProperties(config, testFrameworkName, executor), SMCustomMessagesParsing {
    
    var state: RobotCodeRunProfileState? = null
    
    init {
        
        isUsePredefinedMessageFilter = false
        setIfUndefined(HIDE_PASSED_TESTS, false)
        setIfUndefined(HIDE_IGNORED_TEST, false)
        setIfUndefined(SCROLL_TO_SOURCE, true)
        setIfUndefined(SELECT_FIRST_DEFECT, true)
        setIfUndefined(SHOW_STATISTICS, true)
        
        isIdBasedTestTree = true
        // isPrintTestingStartedTime = true

        // navigating from a failed test opens the first location of its stack trace, the innermost failed keyword
        addStackTraceFilter(RobotCodeConsoleFilter(config.project))
    }
    
    override fun getTestLocator(): SMTestLocator {
        return RobotSMTestLocator()
    }

    // a failure that the test caught before is no place to navigate to
    override fun getErrorNavigatable(location: Location<*>, stacktrace: String): Navigatable? =
        super.getErrorNavigatable(location, failurePathOf(stacktrace))
    
    override fun createTestEventsConverter(
        testFrameworkName: String, consoleProperties: TestConsoleProperties
    ): OutputToGeneralTestEventsConverter {
        if (consoleProperties !is RobotRunnerConsoleProperties) {
            return OutputToGeneralTestEventsConverter(testFrameworkName, consoleProperties)
        }
        val state = consoleProperties.state
        return RobotOutputToGeneralTestEventsConverter(testFrameworkName, state?.debugClient) {
            state?.processHandler?.outputFence?.await()
        }
    }
    
    override fun isEditable(): Boolean {
        return true
    }
    
    // the action finds the failed tests in the results tree of the console
    override fun createRerunFailedTestsAction(consoleView: ConsoleView): AbstractRerunFailedTestsAction? {
        val action = RobotCodeRerunFailedTestsAction(consoleView, config)
        action.init(this)
        (consoleView as? SMTRunnerConsoleView)?.resultsViewer?.let { action.setModel(it) }
        return action
    }
}

