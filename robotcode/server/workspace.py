from typing import Any, Dict, List, Optional

from ..utils.logging import LoggingDescriptor
from .jsonrpc2_server import JsonRPCProtocolPart, TProtocol, rpc_method
from .types import (
    ConfigurationItem,
    ConfigurationParams,
    DidChangeConfigurationParams,
    DidOpenTextDocumentParams,
    TextDocumentItem,
    WorkspaceFolder,
)

__all__ = ["WorkSpaceProtocolPart"]


class WorkSpaceProtocolPart(JsonRPCProtocolPart):

    _logger = LoggingDescriptor()

    def __init__(self, protocol: TProtocol) -> None:
        super().__init__(protocol)
        self.root_uri: Optional[str] = None
        self.root_path: Optional[str] = None
        self.workspace_folders: Optional[List[WorkspaceFolder]] = None
        self._settings: Dict[str, Any] = {}

    def init(
        self,
        root_uri: Optional[str],
        root_path: Optional[str],
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
    ):
        self.root_uri = root_uri
        self.root_path = root_path
        self.workspace_folders = workspace_folders

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @settings.setter
    def settings(self, value: Dict[str, Any]):
        self._settings = value

    @rpc_method(name="workspace/didChangeConfiguration", param_type=DidChangeConfigurationParams)
    @_logger.call
    def _workspace_did_change_configuration(self, settings: Dict[str, Any], *args, **kwargs):
        self.settings = settings

    async def get_configuration(self, section: str, scope_uri: Optional[str] = None) -> List[Any]:
        return (
            await self.protocol.send_request(
                "workspace/configuration",
                ConfigurationParams(items=[ConfigurationItem(scope_uri=scope_uri, section=section)]),
                list,
            )
            or []
        )
