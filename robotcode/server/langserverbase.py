from typing import Any, Dict, Optional

from .jsonrpc import JSONRPC2Connection


class LanguageServerBase:
    def __init__(self, conn: JSONRPC2Connection):
        self.conn = conn
        self.running = True
        self.root_path: Optional[str] = None
        self.root_uri: Optional[str] = None
        self.process_id: Optional[int] = None
        self.trace: Optional[str] = None
        self.client_info = Optional[Dict[str, Any]]
        self.workspace = None

        self.initialization_request_received = False

        self.client_capabilities: Dict[str, Any] = {}

    def __str__(self) -> str:
        return f"{type(self).__name__}(root_path='{self.root_path}', root_uri='{self.root_uri}', trace='{self.trace}', running={self.running}"
