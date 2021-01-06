import uuid
from typing import Any, List, Optional

from .._version import __version__
from ..jsonrpc2.protocol import JsonRPCException, JsonRPCProtocol, ProtocolPartDescriptor, rpc_method
from ..jsonrpc2.server import JsonRPCServer
from ..utils.async_event import AsyncEvent
from ..utils.logging import LoggingDescriptor
from .parts.diagnostics import DiagnosticsProtocolPart
from .parts.documents import TextDocumentProtocolPart
from .parts.window import WindowProtocolPart
from .text_document import TextDocument
from .types import (
    ClientCapabilities,
    InitializedParams,
    InitializeParams,
    InitializeResult,
    SaveOptions,
    ServerCapabilities,
    SetTraceParams,
    TextDocumentSyncKind,
    TextDocumentSyncOptions,
    TraceValue,
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
    documents = ProtocolPartDescriptor(TextDocumentProtocolPart[TextDocument], TextDocument)
    diagnostics = ProtocolPartDescriptor(DiagnosticsProtocolPart[TextDocument])

    def __init__(self, server: Optional[JsonRPCServer[Any]]):
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
        self._trace = TraceValue.OFF

    @property
    def trace(self) -> TraceValue:
        return self._trace

    @trace.setter
    def trace(self, value: TraceValue) -> None:
        self._trace = value

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
        trace: Optional[TraceValue] = None,
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
        **kwargs: Any,
    ) -> InitializeResult:

        self.trace = trace or TraceValue.OFF

        self.client_capabilities = capabilities

        self._workspace = Workspace(self, root_uri=root_uri, root_path=root_path, workspace_folders=workspace_folders)

        self.on_initialize(initialization_options)

        return InitializeResult(
            capabilities=self.capabilities,
            server_info=InitializeResult.ServerInfo(name="robotcode LanguageServer", version=__version__),
        )

    def on_initialize(self, initialization_options: Optional[Any] = None) -> None:
        pass

    @rpc_method(name="initialized", param_type=InitializedParams)
    async def _initialized(self, params: InitializedParams) -> None:
        self.on_initialized()

    def on_initialized(self) -> None:
        pass

    @rpc_method(name="shutdown")
    @_logger.call
    async def shutdown(self) -> None:
        self.shutdown_received = True
        await self.shutdown_event(self, None)

    @rpc_method(name="exit")
    @_logger.call
    def _exit(self) -> None:
        raise SystemExit(0 if self.shutdown_received else 1)

    @rpc_method(name="$/setTrace", param_type=SetTraceParams)
    @_logger.call
    def set_trace(self, value: TraceValue) -> None:
        self.trace = value
