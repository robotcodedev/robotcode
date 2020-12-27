from typing import Any, Dict, List, Optional

from .jsonrpc2_server import JsonRPCProtocol
from .types import ConfigurationItem, ConfigurationParams, WorkspaceFolder

__all__ = ["Workspace"]


class Workspace:
    def __init__(
        self,
        protocol: JsonRPCProtocol,
        root_uri: Optional[str],
        root_path: Optional[str],
        workspace_folders: Optional[List[WorkspaceFolder]],
    ):
        self.protocol = protocol
        self.root_uri = root_uri
        self.root_path = root_path
        self.workspace_folders = workspace_folders
        self._settings: Dict[str, Any] = {}

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"(root_uri='{self.root_uri}', "
            f"root_path={self.root_path}, "
            f"workspace_folders={self.workspace_folders})"
        )

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @settings.setter
    def settings(self, value: Dict[str, Any]):
        self._settings = value

    async def get_configuration(self, section: str, scope_uri: Optional[str] = None) -> List[Any]:
        return (
            await self.protocol.send_request(
                "workspace/configuration",
                ConfigurationParams(items=[ConfigurationItem(scope_uri=scope_uri, section=section)]),
                list,
            )
            or []
        )
