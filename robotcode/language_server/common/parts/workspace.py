from __future__ import annotations

import asyncio
import uuid
import weakref
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import Lock, async_tasking_event, create_sub_task, threaded
from ....utils.dataclasses import from_dict
from ....utils.logging import LoggingDescriptor
from ....utils.path import path_is_relative_to
from ....utils.uri import Uri
from ...common.has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    ApplyWorkspaceEditParams,
    ApplyWorkspaceEditResult,
    ConfigurationItem,
    ConfigurationParams,
    CreateFilesParams,
    DeleteFilesParams,
    DidChangeConfigurationParams,
    DidChangeWatchedFilesParams,
    DidChangeWatchedFilesRegistrationOptions,
    DidChangeWorkspaceFoldersParams,
    DocumentUri,
    FileCreate,
    FileDelete,
    FileEvent,
    FileOperationFilter,
    FileOperationPattern,
    FileOperationRegistrationOptions,
    FileRename,
    FileSystemWatcher,
    Model,
    RenameFilesParams,
    ServerCapabilities,
    ServerCapabilitiesWorkspace,
    ServerCapabilitiesWorkspaceFileOperations,
    TextEdit,
    WatchKind,
    WorkspaceEdit,
)
from ..lsp_types import WorkspaceFolder as TypesWorkspaceFolder
from ..lsp_types import WorkspaceFoldersChangeEvent, WorkspaceFoldersServerCapabilities
from .protocol_part import LanguageServerProtocolPart

__all__ = ["WorkspaceFolder", "Workspace", "ConfigBase", "config_section", "FileWatcherEntry"]

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol


class FileWatcher(NamedTuple):
    glob_pattern: str
    kind: Optional[WatchKind] = None


class FileWatcherEntry:
    def __init__(
        self,
        id: str,
        callback: Callable[[Any, List[FileEvent]], Coroutine[Any, Any, None]],
        watchers: List[FileWatcher],
    ) -> None:
        self.id = id
        self.callback = callback
        self.watchers = watchers
        self.parent: Optional[FileWatcherEntry] = None
        self.finalizer: Any = None

    @async_tasking_event
    async def child_callbacks(sender, changes: List[FileEvent]) -> None:  # NOSONAR
        ...

    async def call_childrens(self, sender: Any, changes: List[FileEvent]) -> None:
        await self.child_callbacks(sender, changes)

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(id={repr(self.id)}, watchers={repr(self.watchers)})"


class WorkspaceFolder:
    def __init__(self, name: str, uri: Uri, document_uri: DocumentUri) -> None:
        super().__init__()
        self.name = name
        self.uri = uri
        self.document_uri = document_uri


def config_section(name: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        setattr(func, "__config_section__", name)
        return func

    return decorator


@runtime_checkable
class HasConfigSection(Protocol):
    __config_section__: str


@config_section("unknown")
@dataclass
class ConfigBase(Model):
    pass


_TConfig = TypeVar("_TConfig", bound=ConfigBase)
_F = TypeVar("_F", bound=Callable[..., Any])


class Workspace(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        parent: LanguageServerProtocol,
        root_uri: Optional[str],
        root_path: Optional[str],
        workspace_folders: Optional[List[TypesWorkspaceFolder]] = None,
    ):
        super().__init__(parent)
        self.root_uri = root_uri

        self.root_path = root_path
        self._workspace_folders_lock = Lock()
        self._workspace_folders: List[WorkspaceFolder] = (
            [WorkspaceFolder(w.name, Uri(w.uri), w.uri) for w in workspace_folders]
            if workspace_folders is not None
            else []
        )
        self._settings: Dict[str, Any] = {}

        self._file_watchers: weakref.WeakSet[FileWatcherEntry] = weakref.WeakSet()
        self._file_watchers_lock = Lock()

        self.parent.on_shutdown.add(self._on_shutdown)

    @property
    def workspace_folders(self) -> List[WorkspaceFolder]:
        return self._workspace_folders

    @_logger.call
    async def _on_shutdown(self, sender: Any) -> None:
        for e in self._file_watchers.copy():
            await self.remove_file_watcher_entry(e)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        capabilities.workspace = ServerCapabilitiesWorkspace(
            workspace_folders=WorkspaceFoldersServerCapabilities(
                supported=True, change_notifications=str(uuid.uuid4())
            ),
            file_operations=ServerCapabilitiesWorkspaceFileOperations(
                did_create=FileOperationRegistrationOptions(
                    filters=[
                        FileOperationFilter(
                            pattern=FileOperationPattern(glob=f"**/*.{{{','.join(self.parent.file_extensions)}}}")
                        )
                    ]
                ),
                will_create=FileOperationRegistrationOptions(
                    filters=[
                        FileOperationFilter(
                            pattern=FileOperationPattern(glob=f"**/*.{{{','.join(self.parent.file_extensions)}}}")
                        )
                    ]
                ),
                did_rename=FileOperationRegistrationOptions(
                    filters=[
                        FileOperationFilter(
                            pattern=FileOperationPattern(glob=f"**/*.{{{','.join(self.parent.file_extensions)}}}")
                        )
                    ]
                ),
                will_rename=FileOperationRegistrationOptions(
                    filters=[
                        FileOperationFilter(
                            pattern=FileOperationPattern(glob=f"**/*.{{{','.join(self.parent.file_extensions)}}}")
                        )
                    ]
                ),
                did_delete=FileOperationRegistrationOptions(
                    filters=[
                        FileOperationFilter(
                            pattern=FileOperationPattern(glob=f"**/*.{{{','.join(self.parent.file_extensions)}}}")
                        )
                    ]
                ),
                will_delete=FileOperationRegistrationOptions(
                    filters=[
                        FileOperationFilter(
                            pattern=FileOperationPattern(glob=f"**/*.{{{','.join(self.parent.file_extensions)}}}")
                        )
                    ]
                ),
            ),
        )

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @settings.setter
    def settings(self, value: Dict[str, Any]) -> None:
        self._settings = value

    @async_tasking_event
    async def did_change_configuration(sender, settings: Dict[str, Any]) -> None:  # NOSONAR
        ...

    @rpc_method(name="workspace/didChangeConfiguration", param_type=DidChangeConfigurationParams)
    @_logger.call
    async def _workspace_did_change_configuration(self, settings: Dict[str, Any], *args: Any, **kwargs: Any) -> None:
        self.settings = settings
        await self.did_change_configuration(self, settings)

    @async_tasking_event
    async def will_create_files(sender, files: List[str]) -> Optional[Mapping[str, List[TextEdit]]]:  # NOSONAR
        ...

    @async_tasking_event
    async def did_create_files(sender, files: List[str]) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def will_rename_files(sender, files: List[Tuple[str, str]]) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def did_rename_files(sender, files: List[Tuple[str, str]]) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def will_delete_files(sender, files: List[str]) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def did_delete_files(sender, files: List[str]) -> None:  # NOSONAR
        ...

    @rpc_method(name="workspace/willCreateFiles", param_type=CreateFilesParams)
    @_logger.call
    async def _workspace_will_create_files(
        self, files: List[FileCreate], *args: Any, **kwargs: Any
    ) -> Optional[WorkspaceEdit]:
        results = await self.will_create_files(self, list(f.uri for f in files))
        if len(results) == 0:
            return None

        result: Dict[str, List[TextEdit]] = {}
        for e in results:
            if e is not None and isinstance(e, Mapping):
                result.update(e)

        # TODO: support full WorkspaceEdit

        return WorkspaceEdit(changes=result)

    @rpc_method(name="workspace/didCreateFiles", param_type=CreateFilesParams)
    @_logger.call
    async def _workspace_did_create_files(self, files: List[FileCreate], *args: Any, **kwargs: Any) -> None:
        await self.did_create_files(self, list(f.uri for f in files))

    @rpc_method(name="workspace/willRenameFiles", param_type=RenameFilesParams)
    @_logger.call
    async def _workspace_will_rename_files(self, files: List[FileRename], *args: Any, **kwargs: Any) -> None:
        await self.will_rename_files(self, list((f.old_uri, f.new_uri) for f in files))

        # TODO: return WorkspaceEdit

    @rpc_method(name="workspace/didRenameFiles", param_type=RenameFilesParams)
    @_logger.call
    async def _workspace_did_rename_files(self, files: List[FileRename], *args: Any, **kwargs: Any) -> None:
        await self.did_rename_files(self, list((f.old_uri, f.new_uri) for f in files))

    @rpc_method(name="workspace/willDeleteFiles", param_type=DeleteFilesParams)
    @_logger.call
    async def _workspace_will_delete_files(self, files: List[FileDelete], *args: Any, **kwargs: Any) -> None:
        await self.will_delete_files(self, list(f.uri for f in files))

        # TODO: return WorkspaceEdit

    @rpc_method(name="workspace/didDeleteFiles", param_type=DeleteFilesParams)
    @_logger.call
    async def _workspace_did_delete_files(self, files: List[FileDelete], *args: Any, **kwargs: Any) -> None:
        await self.did_delete_files(self, list(f.uri for f in files))

    async def get_configuration(
        self, section: Type[_TConfig], scope_uri: Union[str, Uri, None] = None, request: bool = True
    ) -> _TConfig:
        config = await self.get_configuration_raw(
            section=cast(HasConfigSection, section).__config_section__, scope_uri=scope_uri, request=request
        )

        return from_dict(config if config is not None else {}, section)

    async def get_configuration_raw(
        self, section: Optional[str], scope_uri: Union[str, Uri, None] = None, request: bool = True
    ) -> Optional[Any]:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.configuration
            and request
        ):
            r = await self.parent.send_request_async(
                "workspace/configuration",
                ConfigurationParams(
                    items=[
                        ConfigurationItem(
                            scope_uri=str(scope_uri) if isinstance(scope_uri, Uri) else scope_uri,
                            section=section,
                        )
                    ]
                ),
                list,
            )

            return r[0] if r is not None else None

        result = self.settings
        for sub_key in str(section).split("."):
            if sub_key in result:
                result = result.get(sub_key, None)
            else:
                result = {}
                break
        return result

    def get_workspace_folder(self, uri: Union[Uri, str]) -> Optional[WorkspaceFolder]:
        if isinstance(uri, str):
            uri = Uri(uri)

        result = sorted(
            [f for f in self.workspace_folders if path_is_relative_to(uri.to_path(), f.uri.to_path())],
            key=lambda v1: len(v1.uri),
            reverse=True,
        )

        if len(result) > 0:
            return result[0]

        return None

    @rpc_method(name="workspace/didChangeWorkspaceFolders", param_type=DidChangeWorkspaceFoldersParams)
    @_logger.call
    async def _workspace_did_change_workspace_folders(
        self, event: WorkspaceFoldersChangeEvent, *args: Any, **kwargs: Any
    ) -> None:

        async with self._workspace_folders_lock:
            to_remove: List[WorkspaceFolder] = []
            for removed in event.removed:
                to_remove += [w for w in self._workspace_folders if w.uri == removed.uri]

            for removed in event.added:
                to_remove += [w for w in self._workspace_folders if w.uri == removed.uri]

            for r in to_remove:
                self._workspace_folders.remove(r)

            for a in event.added:
                self._workspace_folders.append(WorkspaceFolder(a.name, Uri(a.uri), a.uri))

    @async_tasking_event
    async def did_change_watched_files(sender, changes: List[FileEvent]) -> None:  # NOSONAR
        ...

    @rpc_method(name="workspace/didChangeWatchedFiles", param_type=DidChangeWatchedFilesParams)
    @threaded()
    async def _workspace_did_change_watched_files(self, changes: List[FileEvent], *args: Any, **kwargs: Any) -> None:
        changes = [e for e in changes if not e.uri.endswith("/globalStorage")]
        if changes:
            await self.did_change_watched_files(self, changes)

    async def add_file_watcher(
        self,
        callback: Callable[[Any, List[FileEvent]], Coroutine[Any, Any, None]],
        glob_pattern: str,
        kind: Optional[WatchKind] = None,
    ) -> FileWatcherEntry:
        return await self.add_file_watchers(callback, [(glob_pattern, kind)])

    @_logger.call
    async def add_file_watchers(
        self,
        callback: Callable[[Any, List[FileEvent]], Coroutine[Any, Any, None]],
        watchers: List[Union[FileWatcher, str, Tuple[str, Optional[WatchKind]]]],
    ) -> FileWatcherEntry:

        async with self._file_watchers_lock:
            _watchers = [
                e if isinstance(e, FileWatcher) else FileWatcher(*e) if isinstance(e, tuple) else FileWatcher(e)
                for e in watchers
            ]

            entry = FileWatcherEntry(id=str(uuid.uuid4()), callback=callback, watchers=_watchers)

            current_entry = next((e for e in self._file_watchers if e.watchers == _watchers), None)

            if current_entry is not None:
                if callback not in self.did_change_watched_files:
                    current_entry.child_callbacks.add(callback)  # type: ignore

                entry.parent = current_entry

                if len(current_entry.child_callbacks) > 0:
                    self.did_change_watched_files.add(current_entry.call_childrens)
            else:
                self.did_change_watched_files.add(callback)  # type: ignore

                if (
                    self.parent.client_capabilities
                    and self.parent.client_capabilities.workspace
                    and self.parent.client_capabilities.workspace.did_change_watched_files
                    and self.parent.client_capabilities.workspace.did_change_watched_files.dynamic_registration
                ):
                    await self.parent.register_capability(
                        entry.id,
                        "workspace/didChangeWatchedFiles",
                        DidChangeWatchedFilesRegistrationOptions(
                            watchers=[FileSystemWatcher(glob_pattern=w.glob_pattern, kind=w.kind) for w in _watchers]
                        ),
                    )
                else:
                    # TODO: implement own filewatcher if not supported by language server client
                    self._logger.warning("client did not support workspace/didChangeWatchedFiles.")

            def remove() -> None:
                try:
                    if asyncio.get_running_loop():
                        create_sub_task(self.remove_file_watcher_entry(entry))
                except RuntimeError:
                    pass

            weakref.finalize(entry, remove)

            self._file_watchers.add(entry)

            return entry

    @_logger.call
    async def remove_file_watcher_entry(self, entry: FileWatcherEntry) -> None:
        async with self._file_watchers_lock:
            if entry in self._file_watchers:
                self._file_watchers.remove(entry)

            if entry.parent is not None:
                entry.parent.child_callbacks.remove(entry.callback)  # type: ignore
                if len(entry.child_callbacks) == 0:
                    self.did_change_watched_files.remove(entry.call_childrens)
            elif len(entry.child_callbacks) == 0:
                self.did_change_watched_files.remove(entry.callback)  # type: ignore
                if (
                    self.parent.client_capabilities
                    and self.parent.client_capabilities.workspace
                    and self.parent.client_capabilities.workspace.did_change_watched_files
                    and self.parent.client_capabilities.workspace.did_change_watched_files.dynamic_registration
                ):
                    await self.parent.unregister_capability(entry.id, "workspace/didChangeWatchedFiles")
                # TODO: implement own filewatcher if not supported by language server client

    async def apply_edit(self, edit: WorkspaceEdit, label: Optional[str] = None) -> ApplyWorkspaceEditResult:
        r = await self.parent.send_request_async(
            "workspace/applyEdit", ApplyWorkspaceEditParams(edit, label), return_type=ApplyWorkspaceEditResult
        )

        assert r is not None

        return r
