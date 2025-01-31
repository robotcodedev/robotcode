package dev.robotcode.robotcode4ij.lsp

import org.eclipse.lsp4j.jsonrpc.services.JsonRequest
import org.eclipse.lsp4j.services.LanguageServer
import java.util.concurrent.CompletableFuture


interface RobotCodeServerApi : LanguageServer {
    @JsonRequest("robot/cache/clear") fun clearCache(): CompletableFuture<Void>?
}
