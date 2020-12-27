from asyncio.events import AbstractEventLoop
from typing import List, Optional, Type
import uuid

from .types import (
    ClientCapabilities,
    InitializedParams,
    InitializeParams,
    InitializeResult,
    MessageActionItem,
    MessageType,
    ServerCapabilities,
    ShowMessageParams,
    ShowMessageRequestParams,
    TextDocumentSyncKind,
    WorkspaceFolder,
    WorkspaceFoldersServerCapabilities,
)

from .. import __version__
from .jsonrpc2_server import (
    JsonRPCProtocol,
    JsonRPCServer,
    JsonRpcServerMode,
    StdIoParams,
    TCP_DEFAULT_PORT,
    TcpParams,
    rpc_method,
)
from .logging_helpers import LoggerInstance
from .workspace_handler import WorkSpaceProtocol


class WindowProtocol(JsonRPCProtocol):
    def show_message(self, message: str, type: MessageType = MessageType.Info):
        self.send_notification("window/showMessage", ShowMessageParams(type=type, message=message))

    async def show_message_request(
        self, message: str, actions: List[str] = [], type: MessageType = MessageType.Info
    ) -> MessageActionItem:
        return await self.send_request(
            "window/showMessageRequest",
            ShowMessageRequestParams(type=type, message=message, actions=[MessageActionItem(title=a) for a in actions]),
            return_type=MessageActionItem,
        )


class LanguageServerProtocol(WindowProtocol, WorkSpaceProtocol, JsonRPCProtocol):
    client_capabilities: Optional[ClientCapabilities] = None
    _logger = LoggerInstance()

    @rpc_method(param_type=InitializeParams)
    @_logger.call
    def initialize(
        self,
        capabilities: ClientCapabilities,
        root_path: Optional[str] = None,
        root_uri: Optional[str] = None,
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
        **kwargs,
    ):
        self.client_capabilities = capabilities
        self.workspace = self.create_workspace(
            root_uri=root_uri, root_path=root_path, workspace_folders=workspace_folders
        )
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

    @rpc_method(param_type=InitializedParams)
    @_logger.call
    async def initialized(self, params: InitializedParams):
        pass

    shutdown_received = False

    @rpc_method
    @_logger.call
    def shutdown(self):
        self.workspace = None
        self.shutdown_received = True

    @rpc_method
    @_logger.call
    def exit(self):
        raise SystemExit(0 if self.shutdown_received else 1)


class LanguageServer(JsonRPCServer):
    def __init__(
        self,
        mode: JsonRpcServerMode = JsonRpcServerMode.STDIO,
        stdio_params: StdIoParams = StdIoParams(None, None),
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
        protocol_cls: Type[JsonRPCProtocol] = LanguageServerProtocol,
        loop: Optional[AbstractEventLoop] = None,
        max_workers: Optional[int] = None,
    ):
        super().__init__(
            mode=mode,
            stdio_params=stdio_params,
            tcp_params=tcp_params,
            protocol_cls=protocol_cls,
            loop=loop,
            max_workers=max_workers,
        )
