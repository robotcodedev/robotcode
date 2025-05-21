package dev.robotcode.robotcode4ij.debugging

import com.intellij.openapi.editor.Document
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.TextRange
import com.intellij.psi.PsiFile
import com.intellij.xdebugger.XSourcePosition
import com.intellij.xdebugger.evaluation.EvaluationMode
import com.intellij.xdebugger.evaluation.ExpressionInfo
import com.intellij.xdebugger.evaluation.XDebuggerEvaluator
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import org.eclipse.lsp4j.debug.EvaluateArguments
import org.eclipse.lsp4j.debug.Variable
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer

class RobotCodeDebuggerEvaluator(val debugServer: IDebugProtocolServer, val frame: RobotCodeStackFrame) :
    XDebuggerEvaluator() {
    override fun evaluate(
        expression: String,
        callback: XEvaluationCallback,
        expressionPosition: XSourcePosition?
    ) {
        runBlocking {
            val result = debugServer.evaluate(EvaluateArguments().apply {
                this.expression = expression
                frameId = frame.frame.id
            }).await()
            val variable: Variable = Variable().apply {
                value = result.result
                evaluateName = expression
                variablesReference = result.variablesReference
                type = result.type
                presentationHint = result.presentationHint
            }
            callback.evaluated(
                RobotCodeNamedValue(
                    variable,
                    null,
                    debugServer,
                    frame.session
                )
            )
        }
    }
    
}
