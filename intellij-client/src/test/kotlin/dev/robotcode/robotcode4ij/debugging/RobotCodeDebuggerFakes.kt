package dev.robotcode.robotcode4ij.debugging

import com.intellij.ui.SimpleTextAttributes
import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XDebuggerTreeNodeHyperlink
import com.intellij.xdebugger.frame.XValueChildrenList
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import org.eclipse.lsp4j.debug.EvaluateArguments
import org.eclipse.lsp4j.debug.EvaluateResponse
import org.eclipse.lsp4j.debug.Scope
import org.eclipse.lsp4j.debug.ScopesArguments
import org.eclipse.lsp4j.debug.ScopesResponse
import org.eclipse.lsp4j.debug.SetVariableArguments
import org.eclipse.lsp4j.debug.SetVariableResponse
import org.eclipse.lsp4j.debug.Variable
import org.eclipse.lsp4j.debug.VariablesArguments
import org.eclipse.lsp4j.debug.VariablesArgumentsFilter
import org.eclipse.lsp4j.debug.VariablesResponse
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.ResponseErrorException
import org.eclipse.lsp4j.jsonrpc.messages.ResponseError
import java.util.concurrent.CompletableFuture
import javax.swing.Icon

/**
 * A debugger with fixed scopes, variables, evaluation results and errors that records the `setVariable` and
 * `evaluate` requests. As the RobotCode debugger does, it returns the items of a list only for the `indexed` filter,
 * and the other children for the `named` filter or without a filter.
 */
internal class FakeDebugServer(
    private val scopes: List<Scope> = emptyList(),
    private val variables: Map<Int, List<Variable>> = emptyMap(),
    private val setVariableError: ResponseError? = null,
    private val evaluations: Map<String, EvaluateResponse> = emptyMap(),
    private val evaluationErrors: Map<String, ResponseError> = emptyMap(),
) : IDebugProtocolServer {
    val setVariableRequests = mutableListOf<SetVariableArguments>()
    val evaluateRequests = mutableListOf<EvaluateArguments>()

    override fun scopes(args: ScopesArguments): CompletableFuture<ScopesResponse> {
        return CompletableFuture.completedFuture(ScopesResponse().apply { scopes = this@FakeDebugServer.scopes.toTypedArray() })
    }

    override fun variables(args: VariablesArguments): CompletableFuture<VariablesResponse> {
        val all = variables[args.variablesReference].orEmpty()
        val result = when (args.filter) {
            VariablesArgumentsFilter.INDEXED ->
                all.filter { it.name.toIntOrNull() != null }.drop(args.start ?: 0).take(args.count ?: all.size)
            VariablesArgumentsFilter.NAMED, null -> all.filter { it.name.toIntOrNull() == null }
        }
        return CompletableFuture.completedFuture(VariablesResponse().apply { variables = result.toTypedArray() })
    }

    override fun evaluate(args: EvaluateArguments): CompletableFuture<EvaluateResponse> {
        evaluateRequests.add(args)
        evaluationErrors[args.expression]?.let { return CompletableFuture.failedFuture(ResponseErrorException(it)) }
        return CompletableFuture.completedFuture(evaluations.getValue(args.expression))
    }

    override fun setVariable(args: SetVariableArguments): CompletableFuture<SetVariableResponse> {
        setVariableRequests.add(args)
        return if (setVariableError != null) {
            CompletableFuture.failedFuture(ResponseErrorException(setVariableError))
        } else {
            CompletableFuture.completedFuture(SetVariableResponse())
        }
    }
}

/**
 * A scope whose coroutines run on the calling thread until they wait, so that a request to a [FakeDebugServer], which
 * answers at once, is complete when the call that sent it returns.
 */
internal val immediateScope = CoroutineScope(Dispatchers.Unconfined)

/** A node of the Variables view that records the children added to it. */
internal class RecordingNode : XCompositeNode {
    val children = mutableListOf<XValueChildrenList>()

    override fun addChildren(children: XValueChildrenList, last: Boolean) {
        this.children.add(children)
    }

    @Deprecated("Deprecated in Java")
    override fun tooManyChildren(remaining: Int) = Unit

    override fun setAlreadySorted(alreadySorted: Boolean) = Unit

    override fun setErrorMessage(errorMessage: String) = Unit

    override fun setErrorMessage(errorMessage: String, link: XDebuggerTreeNodeHyperlink?) = Unit

    override fun setMessage(
        message: String, icon: Icon?, attributes: SimpleTextAttributes, link: XDebuggerTreeNodeHyperlink?
    ) = Unit

    override fun isObsolete() = false
}

internal fun variable(name: String, value: String, variablesReference: Int = 0, indexed: Int? = null) = Variable().apply {
    this.name = name
    this.value = value
    this.variablesReference = variablesReference
    indexedVariables = indexed
}

internal fun scope(name: String, variablesReference: Int) = Scope().apply {
    this.name = name
    this.variablesReference = variablesReference
}
