package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XValueChildrenList
import com.intellij.xdebugger.frame.XValueGroup
import kotlinx.coroutines.runBlocking
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

// a scope of a frame, whose variables are requested when the user expands it
class RobotCodeValueGroup(
    groupName: String,
    val variableRef: Int,
    val debugServer: IDebugProtocolServer,
) : XValueGroup(groupName) {
    override fun computeChildren(node: XCompositeNode) {
        val children = runBlocking { debugServer.children(variableRef, planChildren()) }
        node.addChildren(XValueChildrenList().apply {
            children.forEach { add(it.name, RobotCodeNamedValue(it, null, debugServer)) }
        }, true)
    }
}
