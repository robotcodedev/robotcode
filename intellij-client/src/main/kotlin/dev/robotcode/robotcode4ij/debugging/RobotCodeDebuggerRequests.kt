package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XValueChildrenList
import dev.robotcode.robotcode4ij.RobotCodeBundle
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.future.await
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout
import org.eclipse.lsp4j.jsonrpc.ResponseErrorException
import java.util.concurrent.CompletableFuture

/**
 * How long a request to the debugger may take: longer than the 60 seconds that the debugger waits for a keyword
 * evaluated from the debugger, during which it answers no other request.
 */
internal const val DEBUGGER_REQUEST_TIMEOUT_MILLIS = 90_000L

private const val MILLIS_PER_SECOND = 1000L

/** A request that the RobotCode debugger did not answer within the time a request may take. */
internal class DebuggerTimeoutException(timeoutMillis: Long) :
    Exception(RobotCodeBundle.message("debugger.request.timeout", timeoutMillis / MILLIS_PER_SECOND))

/** The answer to a request to the debugger, waited for at most [timeoutMillis]; the request is cancelled after that. */
internal suspend fun <T> CompletableFuture<T>.awaitRequest(timeoutMillis: Long = DEBUGGER_REQUEST_TIMEOUT_MILLIS): T {
    return try {
        withTimeout(timeoutMillis) { await() }
    } catch (_: TimeoutCancellationException) {
        throw DebuggerTimeoutException(timeoutMillis)
    }
}

/** The text that the IDE shows for a failed request: the debugger's own message, or what kept the answer away. */
internal fun requestErrorText(error: Throwable): String {
    return when (error) {
        is ResponseErrorException -> messageOf(error.responseError)
        else -> error.message ?: error.toString()
    }
}

/**
 * Adds the children that [compute] requests to [node] from a coroutine in this scope, or shows why the debugger did not
 * return them; [then] runs after they are added. A node that has become obsolete in the meantime is left as it is.
 */
internal fun CoroutineScope.addChildrenLater(
    node: XCompositeNode, then: () -> Unit = {}, compute: suspend () -> XValueChildrenList
): Job = launch {
    val children = try {
        compute()
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        if (!node.isObsolete) node.setErrorMessage(requestErrorText(e))
        return@launch
    }
    if (!node.isObsolete) {
        node.addChildren(children, true)
        then()
    }
}
