package dev.robotcode.robotcode4ij.debugging

import com.intellij.execution.process.NopProcessHandler
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeDebugProgramRunnerTest {

    // nothing has started the handler of a run whose Robot Framework session did not start
    @Test
    fun aRunWhoseHandlerWasNotStartedEnds() {
        val handler = NopProcessHandler()

        endRun(handler)

        assertTrue(handler.waitFor(5000))
    }
}
