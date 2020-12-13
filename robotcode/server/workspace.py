from typing import Any, Dict, List, Optional

from .lsp import ConfigurationItem, ConfigurationParams

import typing
if typing.TYPE_CHECKING:
    from .language_server_base import LanguageServerBase

__all__ = ["Workspace"]


class Workspace:
    def __init__(self,
                 server: "LanguageServerBase",
                 root_uri: Optional[str],
                 root_path: Optional[str],
                 workspace_folders: Optional[List[str]]):
        self.server = server
        self.root_uri = root_uri
        self.root_path = root_path
        self.workspace_folders = workspace_folders
        self._settings: Dict[str, Any] = {}

    def __str__(self) -> str:
        return f"{type(self).__name__}( root_uri='{self.root_uri}', root_path={self.root_path}, workspace_folders={self.workspace_folders})"  # noqa: E501

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @settings.setter
    def settings(self, value: Dict[str, Any]):
        self._settings = value

    def get_configuration(self, section: str, scope_uri: Optional[str] = None):
        return self.server.conn.send_request(
            "workspace/configuration",
            ConfigurationParams(ConfigurationItem(section, scope_uri)).to_dict()
        ).get("result", None)
