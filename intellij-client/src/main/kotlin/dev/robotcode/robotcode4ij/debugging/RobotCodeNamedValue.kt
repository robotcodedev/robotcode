package dev.robotcode.robotcode4ij.debugging

import com.intellij.icons.AllIcons
import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XNamedValue
import com.intellij.xdebugger.frame.XValueChildrenList
import com.intellij.xdebugger.frame.XValueNode
import com.intellij.xdebugger.frame.XValuePlace
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import org.eclipse.lsp4j.debug.Variable
import org.eclipse.lsp4j.debug.VariablesArguments
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

class RobotCodeNamedValue(
    val variable: Variable, val variableRef: Int?, val debugServer: IDebugProtocolServer, val session: XDebugSession
) : XNamedValue(variable.name ?: "") {
    
    init {
        session.suspendContext?.let {
            val variablesCache = (session.suspendContext as RobotCodeSuspendContext).variablesCache
            variablesCache.getOrDefault((Pair(variableRef, variable.name)), null)?.let {
                variable.value = it.value
                variable.type = it.type ?: variable.type
                variable.variablesReference = variable.variablesReference
                variable.namedVariables = it.namedVariables
                variable.indexedVariables = it.indexedVariables
            }
        }
    }
    
    override fun computePresentation(node: XValueNode, place: XValuePlace) {
        node.setPresentation(AllIcons.Nodes.Variable, variable.type, variable.value, variable.variablesReference != 0)
    }
    
    override fun computeChildren(node: XCompositeNode) {
        runBlocking {
            if (variable.variablesReference != 0) {
                val list = XValueChildrenList()
                debugServer.variables(VariablesArguments().apply { variablesReference = variable.variablesReference })
                    .await().variables.forEach {
                        list.add(
                            it.name, RobotCodeNamedValue(
                                it, variable.variablesReference, debugServer, session
                            )
                        )
                    }
                node.addChildren(list, true)
            }
        }
    }
}
