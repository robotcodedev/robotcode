package dev.robotcode.robotcode4ij.debugging

import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XValueChildrenList
import com.intellij.xdebugger.frame.XValueGroup
import kotlinx.coroutines.CoroutineScope
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

// a scope of a frame, whose variables are requested when the user expands it
class RobotCodeValueGroup(
    groupName: String,
    val variableRef: Int,
    val debugServer: IDebugProtocolServer,
    private val scope: CoroutineScope,
) : XValueGroup(groupName) {
    override fun computeChildren(node: XCompositeNode) {
        scope.addChildrenLater(node) {
            val children = debugServer.children(variableRef, planChildren())
            XValueChildrenList().apply {
                children.forEach { add(it.name, RobotCodeNamedValue(it, null, debugServer, scope)) }
            }
        }
    }
}
