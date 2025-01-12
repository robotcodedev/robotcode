package dev.robotcode.robotcode4ij.debugging

import com.intellij.openapi.vfs.VfsUtil
import com.intellij.ui.ColoredTextContainer
import com.intellij.ui.SimpleTextAttributes
import com.intellij.xdebugger.XDebugSession
import com.intellij.xdebugger.XDebuggerUtil
import com.intellij.xdebugger.XSourcePosition
import com.intellij.xdebugger.evaluation.XDebuggerEvaluator
import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XStackFrame
import com.intellij.xdebugger.frame.XValueChildrenList
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import org.eclipse.lsp4j.debug.ScopesArguments
import org.eclipse.lsp4j.debug.StackFrame
import org.eclipse.lsp4j.debug.VariablesArguments
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import kotlin.io.path.Path

class RobotCodeStackFrame(val frame: StackFrame, val debugServer: IDebugProtocolServer, val session: XDebugSession) :
    XStackFrame() {
    override fun getSourcePosition(): XSourcePosition? {
        val file = VfsUtil.findFile(Path(frame.source?.path ?: return null), false)
        return XDebuggerUtil.getInstance().createPosition(file, frame.line - 1, frame.column)
    }
    
    override fun getEvaluator(): XDebuggerEvaluator {
        return RobotCodeDebuggerEvaluator(debugServer, this)
    }
    
    override fun customizePresentation(component: ColoredTextContainer) {
        if (frame.source == null) {
            component.append(frame.name.orEmpty(), SimpleTextAttributes.REGULAR_ATTRIBUTES)
        } else {
            super.customizePresentation(component)
        }
    }
    
    override fun computeChildren(node: XCompositeNode) {
        // TODO: Implement this method
        runBlocking {
            val scopesResponse = debugServer.scopes(ScopesArguments().apply { frameId = frame.id }).await()
            val list = XValueChildrenList()
            val localScope = scopesResponse.scopes.first { scope -> scope.name.lowercase() == "local" }
            val localVariables = debugServer.variables(VariablesArguments().apply {
                variablesReference = localScope.variablesReference
            }).await()
            localVariables.variables.forEach {
                list.add(
                    it.name,
                    RobotCodeNamedValue(
                        it,
                        localScope.variablesReference,
                        debugServer,
                        session
                    )
                )
            }
            
            scopesResponse.scopes.filter { x -> x.name.lowercase() != "local" }.forEach {
                val variableRef = it.variablesReference
                val groupName = it.name
                val variables = debugServer.variables(VariablesArguments().apply {
                    variablesReference = variableRef
                }).await()
                val group =
                    RobotCodeValueGroup(groupName, variables, variableRef, debugServer, session)
                list.addBottomGroup(group)
            }
            
            node.addChildren(list, true)
        }
    }
}
