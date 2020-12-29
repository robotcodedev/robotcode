import uuid
from typing import List, Optional

from ... import __version__
from ...utils.logging import LoggingDescriptor
from ..jsonrpc2 import JsonRPCException, JsonRPCProtocol, JsonRPCServer, ProtocolPartDescriptor, rpc_method
from .parts.documents import TextDocumentProtocolPart
from .parts.window import WindowProtocolPart
from .parts.workspace import WorkSpaceProtocolPart
from .types import (
    ClientCapabilities,
    InitializedParams,
    InitializeParams,
    InitializeResult,
    SaveOptions,
    ServerCapabilities,
    TextDocumentSyncKind,
    TextDocumentSyncOptions,
    WorkspaceFolder,
    WorkspaceFoldersServerCapabilities,
)

__all__ = ["LanguageServerException", "LanguageServerProtocol"]


class LanguageServerException(JsonRPCException):
    pass


class LanguageServerProtocol(JsonRPCProtocol):

    _logger = LoggingDescriptor()
    window = ProtocolPartDescriptor(WindowProtocolPart)
    workspace = ProtocolPartDescriptor(WorkSpaceProtocolPart)
    documents = ProtocolPartDescriptor(TextDocumentProtocolPart)

    def __init__(self, server: Optional[JsonRPCServer]):
        super().__init__(server)
        self.client_capabilities: Optional[ClientCapabilities] = None
        self.shutdown_received = False
        self.capabilities = ServerCapabilities(
            text_document_sync=TextDocumentSyncOptions(
                open_close=True,
                change=TextDocumentSyncKind.INCREMENTAL,
                will_save=True,
                will_save_wait_until=True,
                save=SaveOptions(include_text=True),
            ),
            workspace=ServerCapabilities.Workspace(
                workspace_folders=WorkspaceFoldersServerCapabilities(
                    supported=True, change_notifications=str(uuid.uuid4())
                )
            ),
        )

    @rpc_method(name="initialize", param_type=InitializeParams)
    @_logger.call
    def _initialize(
        self,
        capabilities: ClientCapabilities,
        root_path: Optional[str] = None,
        root_uri: Optional[str] = None,
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
        **kwargs,
    ):
        self.client_capabilities = capabilities
        self.workspace.init(root_uri=root_uri, root_path=root_path, workspace_folders=workspace_folders)

        return InitializeResult(
            capabilities=self.capabilities,
            server_info=InitializeResult.ServerInfo(name="robotcode LanguageServer", version=__version__),
        )

    @rpc_method(name="initialized", param_type=InitializedParams)
    @_logger.call
    async def _initialized(self, params: InitializedParams):
        pass

    @rpc_method(name="shutdown")
    @_logger.call
    def shutdown(self):
        self.shutdown_received = True

    @rpc_method(name="exit")
    @_logger.call
    def _exit(self):
        raise SystemExit(0 if self.shutdown_received else 1)
