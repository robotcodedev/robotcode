package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.Executor
import com.intellij.execution.testframework.TestConsoleProperties
import com.intellij.execution.testframework.sm.SMCustomMessagesParsing
import com.intellij.execution.testframework.sm.runner.OutputToGeneralTestEventsConverter
import com.intellij.execution.testframework.sm.runner.SMTRunnerConsoleProperties
import com.intellij.execution.testframework.sm.runner.SMTestLocator

class RobotRunnerConsoleProperties(
    config: RobotCodeRunConfiguration, testFrameworkName: String, executor: Executor
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
        isPrintTestingStartedTime = true
    }
    
    override fun getTestLocator(): SMTestLocator {
        return RobotSMTestLocator()
    }
    
    override fun createTestEventsConverter(
        testFrameworkName: String, consoleProperties: TestConsoleProperties
    ): OutputToGeneralTestEventsConverter {
        if (consoleProperties !is RobotRunnerConsoleProperties) {
            return OutputToGeneralTestEventsConverter(testFrameworkName, consoleProperties)
        }
        return RobotOutputToGeneralTestEventsConverter(testFrameworkName, consoleProperties)
    }
    
    override fun isEditable(): Boolean {
        return true
    }
}

