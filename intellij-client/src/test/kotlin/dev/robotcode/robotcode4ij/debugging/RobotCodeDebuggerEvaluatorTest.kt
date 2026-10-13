package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.evaluation.XDebuggerEvaluator
import com.intellij.xdebugger.frame.XValue
import com.intellij.xdebugger.impl.evaluate.XEvaluationOrigin
import com.intellij.xdebugger.impl.ui.tree.nodes.XEvaluationCallbackWithOrigin
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import org.eclipse.lsp4j.debug.EvaluateArguments
import org.eclipse.lsp4j.debug.EvaluateArgumentsContext
import org.eclipse.lsp4j.debug.EvaluateResponse
import org.eclipse.lsp4j.debug.StackFrame
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.messages.ResponseError
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class RobotCodeDebuggerEvaluatorTest {

    // records the result or the error of an evaluation, and the thread that reported it
    private open class Callback : XDebuggerEvaluator.XEvaluationCallback {
        var result: XValue? = null
        var error: String? = null
        var thread: Thread? = null
        val done = CountDownLatch(1)

        override fun evaluated(result: XValue) {
            this.result = result
            thread = Thread.currentThread()
            done.countDown()
        }

        override fun errorOccurred(errorMessage: String) {
            error = errorMessage
            thread = Thread.currentThread()
            done.countDown()
        }
    }

    // a callback as the platform passes it, which tells where the evaluation comes from
    private class CallbackWithOrigin(private val origin: () -> XEvaluationOrigin) : Callback(),
        XEvaluationCallbackWithOrigin {
        override fun getOrigin(): XEvaluationOrigin = origin()
    }

    // a debugger that answers an evaluation only when the test completes [answer]
    private class SlowDebugServer : IDebugProtocolServer {
        val answer = CompletableFuture<EvaluateResponse>()

        override fun evaluate(args: EvaluateArguments): CompletableFuture<EvaluateResponse> = answer
    }

    private fun evaluate(debugServer: IDebugProtocolServer, expression: String, callback: Callback) {
        val frame = RobotCodeStackFrame(StackFrame().apply { id = 1 }, debugServer, immediateScope, 0, true)
        RobotCodeDebuggerEvaluator(debugServer, frame, immediateScope).evaluate(expression, callback, null)
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
        val callback = Callback()

        evaluate(debugServer, "@{items}", callback)
        val node = RecordingNode()
        callback.result!!.computeChildren(node)

        val children = node.children.single()
        assertEquals(listOf("len()", "0", "1", "2"), (0 until children.size()).map { children.getName(it) })
    }

    @Test
    fun theResultArrivesFromABackgroundThreadAfterTheCallHasReturned() {
        val debugServer = SlowDebugServer()
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        val frame = RobotCodeStackFrame(StackFrame().apply { id = 1 }, debugServer, scope, 0, true)
        val callback = Callback()

        RobotCodeDebuggerEvaluator(debugServer, frame, scope).evaluate("Sleep    5s", callback, null)
        assertNull(callback.result)
        debugServer.answer.complete(EvaluateResponse().apply { result = "" })

        assertTrue(callback.done.await(5, TimeUnit.SECONDS))
        assertNotSame(Thread.currentThread(), callback.thread)
        scope.cancel()
    }

    @Test
    fun watchesAndHoversAreExpressionsAndEverythingElseIsReplInput() {
        val contexts = XEvaluationOrigin.entries.associate { origin ->
            origin.name to evaluationContextOf(CallbackWithOrigin { origin })
        }

        assertEquals(
            mapOf(
                "INLINE" to EvaluateArgumentsContext.REPL,
                "DIALOG" to EvaluateArgumentsContext.REPL,
                "WATCH" to EvaluateArgumentsContext.WATCH,
                "INLINE_WATCH" to EvaluateArgumentsContext.WATCH,
                "BREAKPOINT_CONDITION" to EvaluateArgumentsContext.REPL,
                "BREAKPOINT_LOG" to EvaluateArgumentsContext.REPL,
                "RENDERER" to EvaluateArgumentsContext.REPL,
                "EDITOR" to EvaluateArgumentsContext.HOVER,
                "UNSPECIFIED" to EvaluateArgumentsContext.REPL,
                "UNSPECIFIED_WATCH" to EvaluateArgumentsContext.WATCH,
            ),
            contexts
        )
    }

    @Test
    fun aCallbackWithoutOrWithAFailingOriginIsReplInput() {
        assertEquals(EvaluateArgumentsContext.REPL, evaluationContextOf(Callback()))
        assertEquals(EvaluateArgumentsContext.REPL, evaluationContextOf(CallbackWithOrigin { error("no origin") }))
    }

    @Test
    fun theEvaluationSendsTheContextOfItsOrigin() {
        val debugServer = FakeDebugServer(evaluations = mapOf("1 + 2" to EvaluateResponse().apply { result = "3" }))

        evaluate(debugServer, "1 + 2", CallbackWithOrigin { XEvaluationOrigin.WATCH })

        assertEquals(EvaluateArgumentsContext.WATCH, debugServer.evaluateRequests.single().context)
    }

    // the origin is read by reflection, so a platform that renames it would silently turn watches into keyword calls
    @Test
    fun thePlatformStillHasTheOriginThatIsReadByReflection() {
        assertEquals(XEvaluationCallbackWithOrigin::class.java.name, EVALUATION_ORIGIN_INTERFACE)
        assertEquals(
            XEvaluationOrigin::class.java, XEvaluationCallbackWithOrigin::class.java.getMethod("getOrigin").returnType
        )
        val names = XEvaluationOrigin.entries.map { it.name }
        assertTrue(names.containsAll(listOf("WATCH", "INLINE_WATCH", "UNSPECIFIED_WATCH", "EDITOR")))
    }

    @Test
    fun anErrorShowsTheDebuggersMessage() {
        val withBody = ResponseError(
            1, "ExecutionFailed", mapOf("error" to mapOf("format" to "No keyword with name '1 + 2' found."))
        )
        val debugServer = FakeDebugServer(
            evaluationErrors = mapOf("1 + 2" to withBody, "\${x}" to ResponseError(1, "DataError", null))
        )
        val bodyCallback = Callback()
        val messageCallback = Callback()

        evaluate(debugServer, "1 + 2", bodyCallback)
        evaluate(debugServer, "\${x}", messageCallback)

        assertEquals("No keyword with name '1 + 2' found.", bodyCallback.error)
        assertEquals("DataError", messageCallback.error)
        assertNull(bodyCallback.result)
    }
}
