import uuid
from typing import Any, List, Optional

from .._version import __version__
from ..utils.async_event import AsyncEvent
from ..utils.logging import LoggingDescriptor
from ..jsonrpc2.protocol import JsonRPCException, JsonRPCProtocol, ProtocolPartDescriptor, rpc_method
from ..jsonrpc2.server import JsonRPCServer
from .parts.diagnostics import DiagnosticsProtocolPart
from .parts.documents import TextDocumentProtocolPart
from .parts.window import WindowProtocolPart
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
from .workspace import Workspace

__all__ = ["LanguageServerException", "LanguageServerProtocol"]


class LanguageServerException(JsonRPCException):
    pass


class LanguageServerProtocol(JsonRPCProtocol):

    _logger = LoggingDescriptor()

    window = ProtocolPartDescriptor(WindowProtocolPart)
    documents = ProtocolPartDescriptor(TextDocumentProtocolPart)
    diagnostics = ProtocolPartDescriptor(DiagnosticsProtocolPart)

    def __init__(self, server: Optional[JsonRPCServer["LanguageServerProtocol"]]):
        super().__init__(server)
        self._workspace: Optional[Workspace] = None
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

        self.shutdown_event = AsyncEvent[LanguageServerProtocol, None]()

    def workspace(self) -> Optional[Workspace]:
        return self._workspace

    @rpc_method(name="initialize", param_type=InitializeParams)
    @_logger.call
    def _initialize(
        self,
        capabilities: ClientCapabilities,
        root_path: Optional[str] = None,
        root_uri: Optional[str] = None,
        initialization_options: Optional[Any] = None,
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
        **kwargs: Any,
    ) -> InitializeResult:
        self.client_capabilities = capabilities
        self._workspace = Workspace(self, root_uri=root_uri, root_path=root_path, workspace_folders=workspace_folders)

        return InitializeResult(
            capabilities=self.capabilities,
            server_info=InitializeResult.ServerInfo(name="robotcode LanguageServer", version=__version__),
        )

    @rpc_method(name="initialized", param_type=InitializedParams)
    async def _initialized(self, params: InitializedParams) -> None:
        pass

    @rpc_method(name="shutdown")
    @_logger.call
    async def shutdown(self) -> None:
        self.shutdown_received = True
        await self.shutdown_event(self)

    @rpc_method(name="exit")
    @_logger.call
    def _exit(self) -> None:
        raise SystemExit(0 if self.shutdown_received else 1)
