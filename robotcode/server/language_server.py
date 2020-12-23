from robotcode.server.types import (
    ClientCapabilities,
    InitializeParams,
    InitializeResult,
    ServerCapabilities,
    TextDocumentSyncKind,
    WorkspaceFoldersServerCapabilities,
)
from .. import __version__
from .jsonrpc2_server import JsonRPCServer, rpc_method
from .logging_helpers import LoggerInstance
import uuid


class LanguageServer(JsonRPCServer):

    _logger = LoggerInstance()

    @rpc_method(param_type=InitializeParams)
    @_logger.call
    def initialize(self, process_id: str, params: InitializeParams, /, *, capabilities: ClientCapabilities, **kwargs):

        return InitializeResult(
            capabilities=ServerCapabilities(
                text_document_sync=TextDocumentSyncKind.FULL,
                workspace=ServerCapabilities.Workspace(
                    workspace_folders=WorkspaceFoldersServerCapabilities(
                        supported=True, change_notifications=str(uuid.uuid4())
                    )
                ),
            ),
            server_info=InitializeResult.ServerInfo(name="robotcode LanguageServer", version=__version__),
        )

        # return {
        #     "capabilities": {
        #         "textDocumentSync": 1,
        #         #  Avoid complexity of incremental updates for now
        #         # "completionProvider": {
        #         #     "resolveProvider": True,
        #         #     "triggerCharacters": [".", "/"]
        #         # },
        #         # "hoverProvider": True,
        #         # "definitionProvider": True,
        #         # "referencesProvider": True,
        #         # "documentSymbolProvider": True,
        #         # "workspaceSymbolProvider": True,
        #         # "streaming": True,
        #         # "codeActionProvider": {
        #         #     "codeActionKinds": ["source"]
        #         # },
        #         # "documentFormattingProvider": True,
        #         "workspace": {"workspaceFolders": {"supported": True, "changeNotifications": True}},
        #         "documentHighlightProvider": True
        #         # https://github.com/sourcegraph/language-server-protocol/blob/master/extension-files.md#files-extensions-to-lsp
        #         # This is not in the spec yet
        #         # "xfilesProvider": True
        #     },
        #     "serverInfo": {"name": "robotcode LanguageServer", "version": __version__},
        # }
