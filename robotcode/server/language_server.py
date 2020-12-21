from .jsonrpc2_server import (
    JsonRPCErrors,
    JsonRPCNotification,
    JsonRPCRequestMessage,
    JsonRPCResponseMessage,
    JsonRPCServer,
)
from .. import __version__
from .logging_helpers import define_logger
import logging
import inspect


class LanguageServer(JsonRPCServer):
    @define_logger
    def logger(self) -> logging.Logger:
        ...

    @logger.call
    def handle_request(self, message: JsonRPCRequestMessage):

        method_name = "serve_" + message.method

        f = getattr(self, method_name, None)

        if f is None or not callable(f):
            self.send_error(
                JsonRPCErrors.METHOD_NOT_FOUND,
                f"Unknown method: {message.method}",
                id=message.id,
            )
            return

        self.logger.info(str(inspect.signature(f)))

        try:
            self.send_response(message.id, f(**(message.params or {})))
        except BaseException as e:
            self.send_error(JsonRPCErrors.INTERNAL_ERROR, str(e), id=message.id)

    @logger.call
    def handle_notification(self, message: JsonRPCNotification):
        pass

    @logger.call
    def handle_respose(self, message: JsonRPCResponseMessage):
        pass

    @logger.call
    def serve_initialize(self, **kwargs):
        return {
            "capabilities": {
                "textDocumentSync": 1,
                #  Avoid complexity of incremental updates for now
                # "completionProvider": {
                #     "resolveProvider": True,
                #     "triggerCharacters": [".", "/"]
                # },
                # "hoverProvider": True,
                # "definitionProvider": True,
                # "referencesProvider": True,
                # "documentSymbolProvider": True,
                # "workspaceSymbolProvider": True,
                # "streaming": True,
                # "codeActionProvider": {
                #     "codeActionKinds": ["source"]
                # },
                # "documentFormattingProvider": True,
                "workspace": {"workspaceFolders": {"supported": True, "changeNotifications": True}},
                "documentHighlightProvider": True
                # https://github.com/sourcegraph/language-server-protocol/blob/master/extension-files.md#files-extensions-to-lsp
                # This is not in the spec yet
                # "xfilesProvider": True
            },
            "serverInfo": {"name": "robotcode LanguageServer", "version": __version__},
        }
