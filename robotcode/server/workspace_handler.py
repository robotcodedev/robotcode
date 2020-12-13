from typing import Any, Dict, List, Optional

from .language_server_base import LanguageServerBase
from .workspace import Workspace

__all__ = ["WorkSpaceHandler"]


class WorkSpaceHandler(LanguageServerBase):
    def create_workspace(self,
                         root_uri: Optional[str],
                         root_path: Optional[str],
                         workspace_folders: Optional[List[str]]) -> Workspace:
        return Workspace(self, root_uri=root_uri, root_path=root_path, workspace_folders=workspace_folders)

    @LanguageServerBase._debug_call
    def serve_workspace_didChangeConfiguration(self, settings: Dict[str, Any], *args, **kwargs):  # noqa: N802
        if self.workspace is not None:
            self.workspace.settings = settings or {}
