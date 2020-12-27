from typing import Any, Dict, List, Optional

from .jsonrpc2_server import JsonRPCProtocol, rpc_method
from .logging_helpers import LoggerInstance
from .types import DidChangeConfigurationParams, DidOpenTextDocumentParams, TextDocumentItem, WorkspaceFolder
from .workspace import Workspace

__all__ = ["WorkSpaceProtocol"]


class WorkSpaceProtocol(JsonRPCProtocol):
    workspace: Optional[Workspace] = None

    _logger = LoggerInstance()

    def create_workspace(
        self,
        root_uri: Optional[str],
        root_path: Optional[str],
        workspace_folders: Optional[List[WorkspaceFolder]] = None,
    ) -> Workspace:
        return Workspace(self, root_uri=root_uri, root_path=root_path, workspace_folders=workspace_folders)

    @rpc_method(name="workspace/didChangeConfiguration", param_type=DidChangeConfigurationParams)
    @_logger.call
    def workspace_did_change_configuration(self, settings: Dict[str, Any], *args, **kwargs):
        if self.workspace is not None and settings is not None:
            self.workspace.settings = settings

    @rpc_method(name="textDocument/didOpen", param_type=DidOpenTextDocumentParams)
    @_logger.call
    async def text_document_did_open(self, text_document: TextDocumentItem, *args, **kwargs):
        pass
