package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.frame.XValue
import com.intellij.xdebugger.frame.XValueChildrenList
import com.intellij.xdebugger.frame.XValueModifier
import com.intellij.xdebugger.impl.breakpoints.XExpressionImpl
import org.eclipse.lsp4j.debug.StackFrame
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.debug.json.DebugMessageJsonHandler
import org.eclipse.lsp4j.jsonrpc.debug.messages.DebugResponseMessage
import org.eclipse.lsp4j.jsonrpc.services.ServiceEndpoints
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeSetValueTest {

    private class Callback : XValueModifier.XModificationCallback {
        var modified = false
        var error: String? = null

        override fun valueModified() {
            modified = true
        }

        override fun errorOccurred(errorMessage: String) {
            error = errorMessage
        }
    }

    // a frame with the Local, Suite and Global scopes, and a list in the Local scope
    private val debugServer = FakeDebugServer(
        scopes = listOf(scope("Local", 1), scope("Suite", 2), scope("Global", 3)),
        variables = mapOf(
            1 to listOf(
                variable("\${x}", "'abc'"),
                variable("@{items}", "['a', 'b', 'c']", variablesReference = 4, indexed = 3),
            ),
            2 to listOf(variable("\${SUITE_NAME}", "'Sample'")),
            3 to listOf(variable("\${TEMPDIR}", "'/tmp'")),
            4 to listOf(variable("len()", "3"), variable("0", "'a'"), variable("1", "'b'"), variable("2", "'c'")),
        ),
    )

    private val frame = StackFrame().apply {
        id = 1
        name = "Sample.Do Something"
    }

    private fun childrenOf(compute: (RecordingNode) -> Unit): XValueChildrenList {
        return RecordingNode().also(compute).children.single()
    }

    private fun values(children: XValueChildrenList): List<XValue> = (0 until children.size()).map { children.getValue(it) }

    private fun localsOf(innermost: Boolean): XValueChildrenList {
        val stackFrame = RobotCodeStackFrame(frame, debugServer, immediateScope, depth = 2, innermost = innermost)
        return childrenOf { stackFrame.computeChildren(it) }
    }

    @Test
    fun localVariablesOfTheInnermostFrameCanBeChanged() {
        val children = localsOf(innermost = true)

        assertEquals(2, children.size())
        assertTrue(values(children).all { it.modifier != null })
    }

    @Test
    fun localVariablesOfAnOuterFrameCannotBeChanged() {
        val children = localsOf(innermost = false)

        assertEquals(2, children.size())
        assertTrue(values(children).all { it.modifier == null })
    }

    @Test
    fun suiteAndGlobalVariablesCannotBeChanged() {
        val groups = localsOf(innermost = true).bottomGroups

        assertEquals(listOf("Suite", "Global"), groups.map { it.name })
        groups.forEach { group ->
            val children = childrenOf { group.computeChildren(it) }
            assertEquals(1, children.size())
            assertTrue(values(children).all { it.modifier == null })
        }
    }

    @Test
    fun itemsOfAListCannotBeChanged() {
        val list = values(localsOf(innermost = true))[1]

        val children = childrenOf { list.computeChildren(it) }

        assertEquals(listOf("len()", "0", "1", "2"), (0 until children.size()).map { children.getName(it) })
        assertTrue(values(children).all { it.modifier == null })
    }

    @Test
    fun setValueSendsTheScopeReferenceTheNameAndTheText() {
        val modifier = RobotCodeNamedValue(variable("\${x}", "'abc'"), 1, debugServer, immediateScope).modifier!!
        val callback = Callback()

        modifier.setValue(XExpressionImpl.fromText("'changed'"), callback)

        val request = debugServer.setVariableRequests.single()
        assertEquals(1, request.variablesReference)
        assertEquals("\${x}", request.name)
        assertEquals("'changed'", request.value)
        assertTrue(callback.modified)
        assertEquals("'abc'", modifier.initialValueEditorText)
    }

    @Test
    fun anUnchangedStartTextIsNotSent() {
        val modifier =
            RobotCodeNamedValue(variable("@{many}", "[0, 1, 2, ...]"), 1, debugServer, immediateScope).modifier!!
        val callback = Callback()

        modifier.setValue(XExpressionImpl.fromText(modifier.initialValueEditorText), callback)

        assertTrue(debugServer.setVariableRequests.isEmpty())
        assertTrue(callback.modified)
    }

    @Test
    fun aRejectedValueShowsTheDebuggersMessage() {
        // a failed setVariable response as the RobotCode debugger sends it, parsed by lsp4j
        val handler = DebugMessageJsonHandler(ServiceEndpoints.getSupportedMethods(IDebugProtocolServer::class.java))
        handler.setMethodProvider { "setVariable" }
        val response = handler.parseMessage(
            """{"body":{"error":{"format":"DataError: Evaluating expression 'changed' failed","id":-1}},""" +
                """"request_seq":7,"success":false,"command":"setVariable","message":"DataError","type":"response","seq":3}"""
        ) as DebugResponseMessage
        val callback = Callback()

        RobotCodeNamedValue(
            variable("\${x}", "'abc'"), 1, FakeDebugServer(setVariableError = response.error), immediateScope
        ).modifier!!.setValue(XExpressionImpl.fromText("changed"), callback)

        assertEquals("DataError: Evaluating expression 'changed' failed", callback.error)
        assertFalse(callback.modified)
    }
}
