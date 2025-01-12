package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XValueChildrenList
import com.intellij.xdebugger.frame.XValueGroup
import org.eclipse.lsp4j.debug.VariablesResponse
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

class RobotCodeValueGroup(
    groupName: String,
    val variables: VariablesResponse,
    val variableRef: Int,
    val debugServer: IDebugProtocolServer,
    val session: XDebugSession,
) : XValueGroup(groupName) {
    override fun computeChildren(node: XCompositeNode) {
        val list = XValueChildrenList()
        variables.variables.forEach {
            list.add(
                it.name,
                RobotCodeNamedValue(it, variableRef, debugServer, session)
            )
        }
        node.addChildren(list, true)
    }
}
