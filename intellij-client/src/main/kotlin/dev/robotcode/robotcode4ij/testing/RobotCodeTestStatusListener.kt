package dev.robotcode.robotcode4ij.testing

import com.intellij.execution.testframework.AbstractTestProxy
import com.intellij.execution.testframework.TestStatusListener
import com.intellij.openapi.diagnostic.thisLogger

class RobotCodeTestStatusListener : TestStatusListener() {
    override fun testSuiteFinished(root: AbstractTestProxy?) {
        thisLogger().info("Test suite finished: $root")
        // TODO: Implement this method
    }
}
