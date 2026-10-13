package dev.robotcode.robotcode4ij.debugging

import com.intellij.icons.AllIcons
import com.intellij.openapi.vfs.VfsUtil
import com.intellij.ui.ColoredTextContainer
import com.intellij.ui.SimpleTextAttributes
import com.intellij.util.PathUtil
import com.intellij.xdebugger.XDebuggerUtil
import com.intellij.xdebugger.XSourcePosition
import com.intellij.xdebugger.evaluation.XDebuggerEvaluator
import com.intellij.xdebugger.frame.XCompositeNode
import com.intellij.xdebugger.frame.XStackFrame
import com.intellij.xdebugger.frame.XValueChildrenList
import kotlinx.coroutines.CoroutineScope
import org.eclipse.lsp4j.debug.ScopesArguments
import org.eclipse.lsp4j.debug.StackFrame
import org.eclipse.lsp4j.debug.StackFramePresentationHint
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import kotlin.io.path.Path

/**
 * A frame of the stack at a stop, whose requests run in [scope]. [depth] is its distance from the bottom of the stack,
 * and [innermost] is set for the top frame, whose Local variables can be changed.
 */
class RobotCodeStackFrame(
    val frame: StackFrame,
    val debugServer: IDebugProtocolServer,
    private val scope: CoroutineScope,
    private val depth: Int,
    private val innermost: Boolean,
) : XStackFrame() {
    override fun getSourcePosition(): XSourcePosition? {
        val file = VfsUtil.findFile(Path(frame.source?.path ?: return null), false)
        // the debugger counts columns from 1, the position from 0
        return XDebuggerUtil.getInstance().createPosition(file, frame.line - 1, maxOf(frame.column - 1, 0))
    }

    override fun getEvaluator(): XDebuggerEvaluator {
        return RobotCodeDebuggerEvaluator(debugServer, this, scope)
    }

    // without the line, so that the Variables view keeps what the user expanded after a step in the same keyword, test
    // or suite; the depth tells apart the two frames of one stack entry and calls of a keyword at different depths
    override fun getEqualityObject(): Any {
        return Triple(frame.name, frame.source?.path, depth)
    }

    // the name, then the file and line in grey; a frame without a source file, such as a directory suite, is grey
    override fun customizePresentation(component: ColoredTextContainer) {
        val subtle = frame.presentationHint == StackFramePresentationHint.SUBTLE
        component.append(
            frame.name.orEmpty(),
            if (subtle) SimpleTextAttributes.GRAYED_ATTRIBUTES else SimpleTextAttributes.REGULAR_ATTRIBUTES
        )
        val path = frame.source?.path ?: return
        component.append(", ${PathUtil.getFileName(path)}:${frame.line}", SimpleTextAttributes.GRAYED_ATTRIBUTES)
        component.setIcon(AllIcons.Debugger.Frame)
    }

    // the Local variables inline, the other scopes as groups; a frame that is gone because the run went on has no scopes
    override fun computeChildren(node: XCompositeNode) {
        scope.addChildrenLater(node) {
            val list = XValueChildrenList()
            val scopes =
                debugServer.scopes(ScopesArguments().apply { frameId = frame.id }).awaitRequest().scopes.orEmpty()
            val localScope = scopes.firstOrNull { it.name.lowercase() == "local" }
            if (localScope != null) {
                val localScopeReference = localScope.variablesReference.takeIf { innermost }
                debugServer.children(localScope.variablesReference, planChildren()).forEach {
                    list.add(it.name, RobotCodeNamedValue(it, localScopeReference, debugServer, scope))
                }
            }
            scopes.filter { it !== localScope }.forEach {
                list.addBottomGroup(RobotCodeValueGroup(it.name, it.variablesReference, debugServer, scope))
            }
            list
        }
    }
}
