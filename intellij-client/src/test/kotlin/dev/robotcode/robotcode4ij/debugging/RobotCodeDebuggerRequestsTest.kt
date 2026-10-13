package dev.robotcode.robotcode4ij.debugging

import kotlinx.coroutines.runBlocking
import org.eclipse.lsp4j.jsonrpc.ResponseErrorException
import org.eclipse.lsp4j.jsonrpc.messages.ResponseError
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CompletableFuture

class RobotCodeDebuggerRequestsTest {

    @Test
    fun aRequestThatIsNotAnsweredInTimeFailsAndIsCancelled() {
        val request = CompletableFuture<String>()

        val error = assertThrows(DebuggerTimeoutException::class.java) {
            runBlocking { request.awaitRequest(timeoutMillis = 50) }
        }

        assertTrue(request.isCancelled)
        assertEquals("The RobotCode debugger did not answer within 0 seconds.", error.message)
    }

    @Test
    fun anAnsweredRequestReturnsItsAnswer() {
        assertEquals("ok", runBlocking { CompletableFuture.completedFuture("ok").awaitRequest() })
        // a request without a response body, such as `next`, is not mistaken for one that timed out
        assertNull(runBlocking { CompletableFuture.completedFuture<Void?>(null).awaitRequest() })
    }

    @Test
    fun theErrorTextIsTheDebuggersMessage() {
        val body = mapOf("error" to mapOf("format" to "No keyword with name '1 + 2' found."))
        val error = ResponseError(1, "ExecutionFailed", body)

        assertEquals("No keyword with name '1 + 2' found.", requestErrorText(ResponseErrorException(error)))
        assertEquals(
            "ExecutionFailed", requestErrorText(ResponseErrorException(ResponseError(1, "ExecutionFailed", null)))
        )
    }
}
