from typing import Any, Dict, List, Optional

from ...utils.logging import LoggingDescriptor
from ..jsonrpc2.protocol import JsonRPCProtocol, JsonRPCProtocolPart, rpc_method
from .types import ConfigurationItem, ConfigurationParams, DidChangeConfigurationParams, WorkspaceFolder


class Workspace(JsonRPCProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        parent: JsonRPCProtocol,
        root_uri: Optional[str],
        root_path: Optional[str],
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
    ):
        super().__init__(parent)
        self.root_uri = root_uri
        self.root_path = root_path
        self.workspace_folders = workspace_folders
        self._settings: Dict[str, Any] = {}

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @settings.setter
    def settings(self, value: Dict[str, Any]) -> None:
        self._settings = value

    @rpc_method(name="workspace/didChangeConfiguration", param_type=DidChangeConfigurationParams)
    @_logger.call
    def _workspace_did_change_configuration(self, settings: Dict[str, Any], *args: Any, **kwargs: Any) -> None:
        self.settings = settings

    async def get_configuration(self, section: str, scope_uri: Optional[str] = None) -> List[Any]:
        return (
            await self.parent.send_request(
                "workspace/configuration",
                ConfigurationParams(items=[ConfigurationItem(scope_uri=scope_uri, section=section)]),
                list,
            )
            or []
        )
