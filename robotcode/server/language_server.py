import sys
import logging
from typing import Any, Dict, List, Optional

from .jsonrpc import JSONRPC2Error

from robotcode.server.language_server_base import LanguageServerBase
from .lsp import MessageType, TextDocumentSyncKind, to_dict, LSPErrCode
from .workspace_handler import WorkSpaceHandler
from .text_document_handler import TextDocumentHandler

__all__ = ["ServerError", "LanguageServer"]

_log = logging.getLogger(__name__)

# flake8: noqa: N815


class ServerError(Exception):
    def __init__(self, message: str, json_rpc_error: JSONRPC2Error):
        self.message = message
        self.json_rpc_error = json_rpc_error


class LanguageServer(WorkSpaceHandler, TextDocumentHandler, LanguageServerBase):
    def _get_logger(self) -> logging.Logger:
        return _log

    @LanguageServerBase._debug_call
    def run(self):
        while self.running:
            try:
                request = self.conn.read_message()
                self._handle(request)
            except EOFError:
                break
            except ConnectionError as e:
                _log.exception(e)
                break
            except Exception as e:
                _log.exception(e)

        self.running = False

    def _handle(self, client_query):
        is_a_request = "id" in client_query

        if self.premature_request(client_query, is_a_request):
            return

        if self.duplicate_initialization(client_query, is_a_request):
            return

        try:
            response = to_dict(self._dispatch(client_query))

            if is_a_request:
                self.conn.write_response(client_query["id"], response)

        except ServerError as e:
            _log.exception(e)
            if is_a_request:
                self.conn.write_error(
                    client_query["id"],
                    code=e.json_rpc_error.code,
                    message=str(e.json_rpc_error.message),
                    data=e.json_rpc_error.data
                )
        except BaseException as e:
            if is_a_request:
                self.conn.write_error(
                    client_query["id"],
                    code=LSPErrCode.UnknownError,
                    message=str(e)
                )
            raise

    def premature_request(self, client_query, is_a_request):
        if not self.initialization_request_received and \
                client_query.get("method", None) not in ["initialize", "exit"]:
            _log.warning(
                "Client sent a request/notification without initializing")
            if is_a_request:
                self.conn.write_error(
                    client_query["id"],
                    code=LSPErrCode.ServerNotInitialized,
                    message="",
                    data={}
                )
            return True
        else:
            return False

    def duplicate_initialization(self, client_query, is_a_request):
        if self.initialization_request_received and client_query.get("method", None) == "initialize":
            _log.warning("Client sent duplicate initialization")
            if is_a_request:
                self.conn.write_error(
                    client_query["id"],
                    code=LSPErrCode.InvalidRequest,
                    message="Client sent duplicate initialization",
                    data={}
                )
            return True
        else:
            return False

    def _dispatch(self, client_query):
        if not "method" in client_query:
            msg = "Method not specified."
            raise ServerError(msg, JSONRPC2Error(LSPErrCode.MethodNotFound, msg))

        method_name = "serve_" + client_query.get("method").replace("/", "_")

        f = getattr(self, method_name, None)

        if f is None or not callable(f):
            msg = f"Unknown method: {client_query['method']}"
            raise ServerError(msg, JSONRPC2Error(LSPErrCode.MethodNotFound, msg))

        return f(**(client_query.get("params", None) or {}))

    def log_message(self, type: MessageType, message: str):
        self.conn.send_notification(
            "window/logMessage", {"type": type, "message": message})

    @LanguageServerBase._debug_call
    def serve_initialize(self,
                         capabilities: Dict[str, Any] = None,
                         rootPath: Optional[str] = None,
                         rootUri: Optional[str] = None,
                         processId: Optional[int] = None,
                         trace: Optional[str] = None,
                         workspaceFolders: Optional[List[str]] = None,
                         clientInfo: Optional[Dict[str, Any]] = None,
                         **kwargs):
        self.initialization_request_received = True

        self.client_capabilities = capabilities or {}
        self.process_id = processId
        self.trace = trace
        self.client_info = clientInfo

        self.workspace = self.create_workspace(
            root_uri=rootUri, root_path=rootPath, workspace_folders=workspaceFolders)

        return {
            "capabilities": {
                "textDocumentSync": TextDocumentSyncKind.Full.value,
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
                "workspace": {
                    "workspaceFolders": {
                        "supported": True,
                        "changeNotifications": True
                    }
                },
                # https://github.com/sourcegraph/language-server-protocol/blob/master/extension-files.md#files-extensions-to-lsp
                # This is not in the spec yet
                # "xfilesProvider": True
            }
        }

    def serve_initialized(self):
        return {}

    def serve_shutdown(self, **kwargs):
        logging.shutdown()
        self.running = False

    def serve_exit(self, **kwargs):
        sys.exit(0 if not self.running else 1)
