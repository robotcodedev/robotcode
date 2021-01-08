import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..jsonrpc2.protocol import JsonRPCProtocol, JsonRPCProtocolPart, rpc_method
from ..utils.async_event import AsyncEvent
from ..utils.logging import LoggingDescriptor
from .types import (
    ConfigurationItem,
    ConfigurationParams,
    CreateFilesParams,
    DeleteFilesParams,
    DidChangeConfigurationParams,
    FileCreate,
    FileDelete,
    FileOperationFilter,
    FileOperationPattern,
    FileOperationRegistrationOptions,
    FileRename,
    RenameFilesParams,
    ServerCapabilities,
    WorkspaceFolder,
    WorkspaceFoldersServerCapabilities,
)


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

        self.will_create_files = AsyncEvent[Workspace, List[str]]()
        self.did_create_files = AsyncEvent[Workspace, List[str]]()
        self.will_rename_files = AsyncEvent[Workspace, List[Tuple[str, str]]]()
        self.did_rename_files = AsyncEvent[Workspace, List[Tuple[str, str]]]()
        self.will_delete_files = AsyncEvent[Workspace, List[str]]()
        self.did_delete_files = AsyncEvent[Workspace, List[str]]()

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        capabilities.workspace = ServerCapabilities.Workspace(
            workspace_folders=WorkspaceFoldersServerCapabilities(
                supported=True, change_notifications=str(uuid.uuid4())
            ),
            file_operations=ServerCapabilities.Workspace.FileOperations(
                did_create=FileOperationRegistrationOptions(
                    filters=[FileOperationFilter(pattern=FileOperationPattern(glob="**/*"))]
                ),
                will_create=FileOperationRegistrationOptions(
                    filters=[FileOperationFilter(pattern=FileOperationPattern(glob="**/*"))]
                ),
                did_rename=FileOperationRegistrationOptions(
                    filters=[FileOperationFilter(pattern=FileOperationPattern(glob="**/*"))]
                ),
                will_rename=FileOperationRegistrationOptions(
                    filters=[FileOperationFilter(pattern=FileOperationPattern(glob="**/*"))]
                ),
                did_delete=FileOperationRegistrationOptions(
                    filters=[FileOperationFilter(pattern=FileOperationPattern(glob="**/*"))]
                ),
                will_delete=FileOperationRegistrationOptions(
                    filters=[FileOperationFilter(pattern=FileOperationPattern(glob="**/*"))]
                ),
            ),
        )

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

    @rpc_method(name="workspace/willCreateFiles", param_type=CreateFilesParams)
    @_logger.call
    async def _workspace_will_create_files(self, files: List[FileCreate], *args: Any, **kwargs: Any) -> None:
        await self.will_create_files(self, list(f.uri for f in files))

    @rpc_method(name="workspace/didCreateFiles", param_type=CreateFilesParams)
    @_logger.call
    async def _workspace_did_create_files(self, files: List[FileCreate], *args: Any, **kwargs: Any) -> None:
        await self.did_create_files(self, list(f.uri for f in files))

    @rpc_method(name="workspace/willRenameFiles", param_type=RenameFilesParams)
    @_logger.call
    async def _workspace_will_rename_files(self, files: List[FileRename], *args: Any, **kwargs: Any) -> None:
        await self.will_rename_files(self, list((f.old_uri, f.new_uri) for f in files))

    @rpc_method(name="workspace/didRenameFiles", param_type=RenameFilesParams)
    @_logger.call
    async def _workspace_did_rename_files(self, files: List[FileRename], *args: Any, **kwargs: Any) -> None:
        await self.did_rename_files(self, list((f.old_uri, f.new_uri) for f in files))

    @rpc_method(name="workspace/willDeleteFiles", param_type=DeleteFilesParams)
    @_logger.call
    async def _workspace_will_delete_files(self, files: List[FileDelete], *args: Any, **kwargs: Any) -> None:
        await self.will_delete_files(self, list(f.uri for f in files))

    @rpc_method(name="workspace/didDeleteFiles", param_type=DeleteFilesParams)
    @_logger.call
    async def _workspace_did_delete_files(self, files: List[FileDelete], *args: Any, **kwargs: Any) -> None:
        await self.did_delete_files(self, list(f.uri for f in files))

    async def get_configuration(self, section: str, scope_uri: Optional[str] = None) -> List[Any]:
        return (
            await self.parent.send_request(
                "workspace/configuration",
                ConfigurationParams(items=[ConfigurationItem(scope_uri=scope_uri, section=section)]),
                list,
            )
            or []
        )
