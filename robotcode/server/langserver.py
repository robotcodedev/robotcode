import sys
import logging
from typing import Any, Dict, List, Optional

from .jsonrpc import JSONRPC2Error

from robotcode.server.langserverbase import LanguageServerBase
from .lsp import MessageType, TextDocumentSyncKind, to_dict, LSPErrCode

logger = logging.getLogger(__name__)
logger.propagate = True

logging.getLogger("robotcode.server.jsonrpc").propagate = False

# flake8: noqa: N815


class ServerError(Exception):
    def __init__(self, server_error_message, json_rpc_error):
        self.server_error_message: str = server_error_message
        self.json_rpc_error: JSONRPC2Error = json_rpc_error


def _log_call(func):

    def wrapper(*args, **kwargs):
        self: LanguageServer = args[0]
        msg = f"Calling {func.__qualname__}({', '.join(repr(a) for a in args)}{(', '+', '.join(f'{str(k)}={repr(v)}' for k,v in kwargs.items())) if len(kwargs)>0 else ''})"
        logger.debug(msg)
        return func(*args, **kwargs)

    return wrapper


class LanguageServer(LanguageServerBase):
    def run(self):
        while self.running:
            try:
                request = self.conn.read_message()
                self.handle(request)
            except EOFError:
                break
            except Exception as e:
                logger.error("Unexpected error: %s", e, exc_info=True)

    def handle(self, client_query):
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
            logger.error(e.server_error_message)

            let_client_know_of_errors = False
            if let_client_know_of_errors:
                self.conn.write_error(
                    client_query["id"],
                    code=e.json_rpc_error.code,
                    message=str(e.json_rpc_error.message),
                    data=e.json_rpc_error.data)

    def premature_request(self, client_query, is_a_request):
        if not self.initialization_request_received and \
                client_query.get("method", None) not in ["initialize", "exit"]:
            logger.warning(
                "Client sent a request/notification without initializing")
            if is_a_request:
                self.conn.write_error(
                    client_query["id"],
                    code=LSPErrCode.ServerNotInitialized,
                    message="",
                    data={})
            return True
        else:
            return False

    def duplicate_initialization(self, client_query, is_a_request):
        if self.initialization_request_received and client_query.get("method", None) == "initialize":
            logger.warning("Client sent duplicate initialization")
            if is_a_request:
                self.conn.write_error(
                    client_query["id"],
                    code=LSPErrCode.InvalidRequest,
                    message="Client sent duplicate initialization",
                    data={})
            return True
        else:
            return False

    def _dispatch(self, client_query):
        method_name = "serve_" + \
            client_query.get("method", "noMethod").replace("/", "_")
        try:
            f = getattr(self, method_name)
        except AttributeError:
            msg = f"Unknown method: {client_query['method']}"
            raise ServerError(server_error_message=msg,
                              json_rpc_error=JSONRPC2Error(code=LSPErrCode.MethodNotFound, message=msg))

        return f(**(client_query.get("params", None) or {}))

    def log_message(self, type: MessageType, message: str):
        self.conn.send_notification(
            "window/logMessage", {"type": type, "message": message})

    @_log_call
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
        self.root_path = rootPath
        self.root_uri = rootUri
        self.process_id = processId
        self.trace = trace
        self.client_info = clientInfo

        return {
            "capabilities": {
                "textDocumentSync": TextDocumentSyncKind.Full,
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
