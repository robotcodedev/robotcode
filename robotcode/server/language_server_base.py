from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from .jsonrpc import JSONRPC2Connection
from .workspace import Workspace

from .logging_handler import LoggingHandler

__all__ = ["LanguageServerBase"]


class LanguageServerBase(LoggingHandler, ABC):
    def __init__(self, conn: JSONRPC2Connection):
        self.conn = conn
        self.running = True
        self.process_id: Optional[int] = None
        self.trace: Optional[str] = None
        self.client_info = Optional[Dict[str, Any]]
        self.workspace: Optional[Workspace] = None

        self.initialization_request_received = False

        self.client_capabilities: Dict[str, Any] = {}

    @abstractmethod
    def create_workspace(self,
                         root_uri: Optional[str],
                         root_path: Optional[str],
                         workspace_folders: Optional[List[str]]) -> Workspace:
        ...

    def __str__(self) -> str:
        return f"{type(self).__name__}( trace='{self.trace}', running={self.running}, workspace='{self.workspace}')"
