package dev.robotcode.robotcode4ij.lsp

import org.eclipse.lsp4j.jsonrpc.services.JsonRequest
import org.eclipse.lsp4j.services.LanguageServer
import java.util.concurrent.CompletableFuture


interface RobotCodeServerApi : LanguageServer {
    @JsonRequest("robot/cache/clear") fun clearCache(): CompletableFuture<Void>?

    @JsonRequest("robot/projectInfo") fun projectInfo(): CompletableFuture<ProjectInfo>?
}

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
