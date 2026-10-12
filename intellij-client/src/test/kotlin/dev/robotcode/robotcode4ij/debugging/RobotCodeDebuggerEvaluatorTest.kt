package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.evaluation.XDebuggerEvaluator
import com.intellij.xdebugger.frame.XValue
import org.eclipse.lsp4j.debug.EvaluateResponse
import org.eclipse.lsp4j.debug.StackFrame
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeDebuggerEvaluatorTest {

    // records the result of an evaluation
    private class Callback : XDebuggerEvaluator.XEvaluationCallback {
        var result: XValue? = null

        override fun evaluated(result: XValue) {
            this.result = result
        }

        override fun errorOccurred(errorMessage: String) = Unit
    }

    @Test
    fun aListResultExpandsIntoItsItems() {
        // the RobotCode debugger reports a list with `len()` as its named and the items as its indexed children
        val debugServer = FakeDebugServer(
            variables = mapOf(
                4 to listOf(variable("len()", "3"), variable("0", "'a'"), variable("1", "'b'"), variable("2", "'c'")),
            ),
            evaluations = mapOf("@{items}" to EvaluateResponse().apply {
                result = "['a', 'b', 'c']"
                type = "<class 'list'>"
                variablesReference = 4
                namedVariables = 1
                indexedVariables = 3
            }),
        )
        val frame = RobotCodeStackFrame(StackFrame().apply { id = 1 }, debugServer, depth = 0, innermost = true)
        val callback = Callback()

        RobotCodeDebuggerEvaluator(debugServer, frame).evaluate("@{items}", callback, null)
        val node = RecordingNode()
        callback.result!!.computeChildren(node)

        val children = node.children.single()
        assertEquals(listOf("len()", "0", "1", "2"), (0 until children.size()).map { children.getName(it) })
    }
}
