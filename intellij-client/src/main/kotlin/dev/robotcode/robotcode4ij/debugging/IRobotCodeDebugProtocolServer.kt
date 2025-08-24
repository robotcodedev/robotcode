package dev.robotcode.robotcode4ij.debugging

import org.eclipse.lsp4j.debug.CancelArguments
import org.eclipse.lsp4j.debug.services.IDebugProtocolServer
import org.eclipse.lsp4j.jsonrpc.services.JsonRequest
import java.util.concurrent.CompletableFuture

interface IRobotCodeDebugProtocolServer: IDebugProtocolServer {
    @JsonRequest("robot/sync") fun robotSync(): CompletableFuture<Void?>? {
        throw UnsupportedOperationException()
    }
}
