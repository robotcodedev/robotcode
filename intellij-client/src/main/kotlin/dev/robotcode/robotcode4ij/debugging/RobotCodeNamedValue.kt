package dev.robotcode.robotcode4ij.debugging

import com.intellij.icons.AllIcons
import com.intellij.xdebugger.XExpression
import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XNamedValue
import com.intellij.xdebugger.frame.XValueChildrenList
import com.intellij.xdebugger.frame.XValueModifier
import com.intellij.xdebugger.frame.XValueNode
import com.intellij.xdebugger.frame.XValuePlace
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import org.eclipse.lsp4j.debug.SetVariableArguments
import org.eclipse.lsp4j.debug.Variable
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.messages.ResponseError

/**
 * A variable or a child of one, whose requests run in [scope]. [localScopeReference] is set only for a variable
 * directly in the Local scope of the innermost frame: the debugger assigns a new value in the innermost variable scope
 * of the run, so only such a variable can be changed where the Variables view shows it.
 */
class RobotCodeNamedValue(
    val variable: Variable, private val localScopeReference: Int?, val debugServer: IDebugProtocolServer,
    private val scope: CoroutineScope,
) : XNamedValue(variable.name ?: "") {

    override fun computePresentation(node: XValueNode, place: XValuePlace) {
        node.setPresentation(
            AllIcons.Nodes.Variable, typeName(variable.type), variable.value, variable.variablesReference != 0
        )
    }

    override fun computeChildren(node: XCompositeNode) {
        if (variable.variablesReference != 0) {
            addChildren(node, 0)
        }
    }

    // the children from [start] on; the items that remain are offered as the next page
    private fun addChildren(node: XCompositeNode, start: Int) {
        val plan = planChildren(variable.indexedVariables, start)
        scope.addChildrenLater(node, then = {
            if (plan.remaining > 0) {
                node.tooManyChildren(plan.remaining) { addChildren(node, plan.next) }
            }
        }) {
            val children = debugServer.children(variable.variablesReference, plan)
            XValueChildrenList().apply {
                children.forEach { add(it.name, RobotCodeNamedValue(it, null, debugServer, scope)) }
            }
        }
    }

    override fun getModifier(): XValueModifier? {
        val scopeReference = localScopeReference ?: return null
        return object : XValueModifier() {
            override fun getInitialValueEditorText(): String? = variable.value

            // the start text is the value as the debugger shows it, which it shortens for long values, so an unchanged
            // text is not sent: it would replace the variable with the shortened value
            override fun setValue(expression: XExpression, callback: XModificationCallback) {
                if (expression.expression == variable.value) {
                    callback.valueModified()
                    return
                }
                scope.launch {
                    val error = try {
                        debugServer.setVariable(SetVariableArguments().apply {
                            variablesReference = scopeReference
                            name = variable.name
                            value = expression.expression
                        }).awaitRequest()
                        null
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Exception) {
                        requestErrorText(e)
                    }
                    if (error == null) callback.valueModified() else callback.errorOccurred(error)
                }
            }
        }
    }
}

// the debugger sends the name of the exception as the message and the whole text in the body of the error, which
// lsp4j passes on as a map
internal fun messageOf(error: ResponseError): String {
    val format = ((error.data as? Map<*, *>)?.get("error") as? Map<*, *>)?.get("format") as? String
    return format ?: error.message
}
