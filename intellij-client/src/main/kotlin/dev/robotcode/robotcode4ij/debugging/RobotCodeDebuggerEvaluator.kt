package dev.robotcode.robotcode4ij.debugging

import com.intellij.openapi.application.runReadActionBlocking
import com.intellij.openapi.diagnostic.thisLogger
import com.intellij.openapi.editor.Document
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.project.Project
import com.intellij.xdebugger.XSourcePosition
import com.intellij.xdebugger.evaluation.ExpressionInfo
import com.intellij.xdebugger.evaluation.XDebuggerEvaluator
import com.redhat.devtools.lsp4ij.LSPIJUtils
import com.redhat.devtools.lsp4ij.LanguageServerManager
import com.redhat.devtools.lsp4ij.ServerStatus
import dev.robotcode.robotcode4ij.lsp.EvaluatableExpression
import dev.robotcode.robotcode4ij.lsp.EvaluatableExpressionParams
import dev.robotcode.robotcode4ij.lsp.RobotCodeLanguageServerManager
import dev.robotcode.robotcode4ij.lsp.RobotCodeServerApi
import dev.robotcode.robotcode4ij.lsp.langServerManager
import kotlinx.coroutines.future.await
import kotlinx.coroutines.runBlocking
import org.eclipse.lsp4j.TextDocumentIdentifier
import org.eclipse.lsp4j.debug.EvaluateArguments
import org.eclipse.lsp4j.debug.Variable
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.jetbrains.concurrency.AsyncPromise
import org.jetbrains.concurrency.Promise
import org.jetbrains.concurrency.resolvedPromise
import java.util.concurrent.CompletableFuture
import java.util.concurrent.TimeUnit

private const val HOVER_TIMEOUT_SECONDS = 2L

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
                namedVariables = result.namedVariables
                indexedVariables = result.indexedVariables
                type = result.type
                presentationHint = result.presentationHint
            }
            callback.evaluated(
                RobotCodeNamedValue(
                    variable,
                    null,
                    debugServer
                )
            )
        }
    }

    // the language server names the variable under the mouse; the debugger evaluates a single variable as its value, so
    // a hover never runs a keyword. A hover does not start a stopped language server.
    override fun getExpressionInfoAtOffsetAsync(
        project: Project, document: Document, offset: Int, sideEffectsAllowed: Boolean
    ): Promise<ExpressionInfo?> {
        val file = FileDocumentManager.getInstance().getFile(document)
        if (file == null || project.langServerManager.status != ServerStatus.started) return resolvedPromise(null)
        val params = runReadActionBlocking {
            EvaluatableExpressionParams(
                TextDocumentIdentifier(LSPIJUtils.toUriAsString(file)), LSPIJUtils.toPosition(offset, document)
            )
        }
        val promise = AsyncPromise<ExpressionInfo?>()
        LanguageServerManager.getInstance(project).getLanguageServer(RobotCodeLanguageServerManager.LANGUAGE_SERVER_ID)
            .thenCompose {
                (it?.server as? RobotCodeServerApi)?.getEvaluatableExpression(params)
                    ?: CompletableFuture.completedFuture(null)
            }
            .orTimeout(HOVER_TIMEOUT_SECONDS, TimeUnit.SECONDS)
            .whenComplete { expression, error ->
                if (error != null) {
                    thisLogger().debug("The language server named no expression for a hover", error)
                    promise.setResult(null)
                } else {
                    promise.setResult(runReadActionBlocking { expressionInfoOf(document, expression) })
                }
            }
        return promise
    }
}

/** The hover expression at the range the language server reported, or null when it reported none. */
internal fun expressionInfoOf(document: Document, expression: EvaluatableExpression?): ExpressionInfo? {
    val range = expression?.range ?: return null
    val textRange = LSPIJUtils.toTextRange(range, document) ?: return null
    return ExpressionInfo(textRange, expression.expression ?: document.getText(textRange))
}
