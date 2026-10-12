package dev.robotcode.robotcode4ij.lsp

import org.eclipse.lsp4j.Position
import org.eclipse.lsp4j.Range
import org.eclipse.lsp4j.TextDocumentIdentifier
import org.eclipse.lsp4j.jsonrpc.services.JsonRequest
import org.eclipse.lsp4j.services.LanguageServer
import java.util.concurrent.CompletableFuture


interface RobotCodeServerApi : LanguageServer {
    @JsonRequest("robot/cache/clear") fun clearCache(): CompletableFuture<Void>?

    @JsonRequest("robot/projectInfo") fun projectInfo(): CompletableFuture<ProjectInfo>?

    @JsonRequest("robot/debugging/getEvaluatableExpression")
    fun getEvaluatableExpression(params: EvaluatableExpressionParams): CompletableFuture<EvaluatableExpression?>?
}

/** The document and position for which the language server names the variable there. */
data class EvaluatableExpressionParams(val textDocument: TextDocumentIdentifier, val position: Position)

/** The range and name of the variable at a position, as the language server reports it. */
data class EvaluatableExpression(val range: Range? = null, val expression: String? = null)

/**
 * The versions that the language server reports for the project; the Robocop version is missing without Robocop.
 */
data class ProjectInfo(
    val robotVersionString: String? = null,
    val robocopVersionString: String? = null,
    val pythonVersionString: String? = null,
    val pythonExecutable: String? = null,
    val robotCodeVersionString: String? = null
)
