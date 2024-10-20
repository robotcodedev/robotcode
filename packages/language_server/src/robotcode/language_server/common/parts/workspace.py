import threading
import uuid
import weakref
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Final,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from robotcode.core.concurrent import Task
from robotcode.core.event import event
from robotcode.core.filewatcher import FileWatcher, FileWatcherEntry, FileWatcherManagerBase
from robotcode.core.lsp.types import (
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
    FileCreate,
    FileDelete,
    FileEvent,
    FileOperationFilter,
    FileOperationOptions,
    FileOperationPattern,
    FileOperationRegistrationOptions,
    FileRename,
    FileSystemWatcher,
    RenameFilesParams,
    ServerCapabilities,
    ServerCapabilitiesWorkspaceType,
    TextDocumentEdit,
    TextEdit,
    WatchKind,
    WorkspaceEdit,
    WorkspaceFoldersChangeEvent,
    WorkspaceFoldersServerCapabilities,
)
from robotcode.core.lsp.types import WorkspaceFolder as TypesWorkspaceFolder
from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import from_dict
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.workspace import ConfigBase, TConfig, WorkspaceFolder
from robotcode.core.workspace import Workspace as CoreWorkspace
from robotcode.jsonrpc2.protocol import rpc_method

from .protocol_part import LanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


class Workspace(LanguageServerProtocolPart, CoreWorkspace, FileWatcherManagerBase):
    _logger: Final = LoggingDescriptor()

    def __init__(
        self,
        parent: "LanguageServerProtocol",
        root_uri: Optional[str],
        root_path: Optional[str],
        workspace_folders: Optional[List[TypesWorkspaceFolder]] = None,
    ):
        super().__init__(parent)

        self.root_path = root_path

        if root_path is not None and root_uri is None:
            root_uri = str(Uri.from_path(root_path))

        CoreWorkspace.__init__(
            self,
            Uri(root_uri) if root_uri else None,
            [WorkspaceFolder(w.name, Uri(w.uri)) for w in workspace_folders] if workspace_folders is not None else [],
        )

        self._file_watchers: weakref.WeakSet[FileWatcherEntry] = weakref.WeakSet()
        self._file_watchers_lock = threading.RLock()

        self.parent.on_shutdown.add(self.server_shutdown)
        self.parent.on_initialize.add(self.server_initialize)

        self._settings_cache: Dict[Tuple[Optional[WorkspaceFolder], str], ConfigBase] = {}

    def server_initialize(self, sender: Any, initialization_options: Optional[Any] = None) -> None:
        if (
            initialization_options is not None
            and isinstance(initialization_options, dict)
            and "settings" in initialization_options
        ):
            self.settings = initialization_options["settings"]

    @property
    def workspace_folders(self) -> List[WorkspaceFolder]:
        with self._workspace_folders_lock:
            return self._workspace_folders

    @_logger.call
    def server_shutdown(self, sender: Any) -> None:
        for e in self._file_watchers.copy():
            self.remove_file_watcher_entry(e)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        capabilities.workspace = ServerCapabilitiesWorkspaceType(
            workspace_folders=WorkspaceFoldersServerCapabilities(
                supported=True, change_notifications=str(uuid.uuid4())
            ),
            file_operations=FileOperationOptions(
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

    @event
    def did_change_configuration(sender, settings: Dict[str, Any]) -> None: ...

    @rpc_method(name="workspace/didChangeConfiguration", param_type=DidChangeConfigurationParams)
    def _workspace_did_change_configuration(self, settings: Dict[str, Any], *args: Any, **kwargs: Any) -> None:
        self.settings = settings
        self._settings_cache.clear()
        self.did_change_configuration(self, settings)

    @event
    def will_create_files(sender, files: List[str]) -> Optional[Mapping[str, List[TextEdit]]]: ...

    @event
    def did_create_files(sender, files: List[str]) -> None: ...

    @event
    def will_rename_files(sender, files: List[Tuple[str, str]]) -> None: ...

    @event
    def did_rename_files(sender, files: List[Tuple[str, str]]) -> None: ...

    @event
    def will_delete_files(sender, files: List[str]) -> None: ...

    @event
    def did_delete_files(sender, files: List[str]) -> None: ...

    @rpc_method(name="workspace/willCreateFiles", param_type=CreateFilesParams, threaded=True)
    def _workspace_will_create_files(
        self, files: List[FileCreate], *args: Any, **kwargs: Any
    ) -> Optional[WorkspaceEdit]:
        results = self.will_create_files(self, [f.uri for f in files])
        if len(results) == 0:
            return None

        result: Dict[str, List[TextEdit]] = {}
        for e in results:
            if e is not None and isinstance(e, Mapping):
                result.update(e)

        # TODO: support full WorkspaceEdit

        return WorkspaceEdit(changes=result)

    @rpc_method(name="workspace/didCreateFiles", param_type=CreateFilesParams, threaded=True)
    def _workspace_did_create_files(self, files: List[FileCreate], *args: Any, **kwargs: Any) -> None:
        self.did_create_files(self, [f.uri for f in files])

    @rpc_method(name="workspace/willRenameFiles", param_type=RenameFilesParams, threaded=True)
    def _workspace_will_rename_files(self, files: List[FileRename], *args: Any, **kwargs: Any) -> None:
        self.will_rename_files(self, [(f.old_uri, f.new_uri) for f in files])

        # TODO: return WorkspaceEdit

    @rpc_method(name="workspace/didRenameFiles", param_type=RenameFilesParams, threaded=True)
    def _workspace_did_rename_files(self, files: List[FileRename], *args: Any, **kwargs: Any) -> None:
        self.did_rename_files(self, [(f.old_uri, f.new_uri) for f in files])

    @rpc_method(name="workspace/willDeleteFiles", param_type=DeleteFilesParams, threaded=True)
    def _workspace_will_delete_files(self, files: List[FileDelete], *args: Any, **kwargs: Any) -> None:
        self.will_delete_files(self, [f.uri for f in files])

        # TODO: return WorkspaceEdit

    @rpc_method(name="workspace/didDeleteFiles", param_type=DeleteFilesParams, threaded=True)
    def _workspace_did_delete_files(self, files: List[FileDelete], *args: Any, **kwargs: Any) -> None:
        self.did_delete_files(self, [f.uri for f in files])

    def get_configuration(
        self,
        section: Type[TConfig],
        scope_uri: Union[str, Uri, None] = None,
    ) -> TConfig:
        return self.get_configuration_future(section, scope_uri).result(30)

    def get_configuration_future(
        self,
        section: Type[TConfig],
        scope_uri: Union[str, Uri, None] = None,
    ) -> Task[TConfig]:
        result_future: Task[TConfig] = Task()

        scope = self.get_workspace_folder(scope_uri) if scope_uri is not None else None

        if (scope, section.__config_section__) in self._settings_cache:
            result_future.set_result(
                cast(
                    TConfig,
                    self._settings_cache[(scope, section.__config_section__)],
                )
            )
            return result_future

        def _get_configuration_done(f: Task[Optional[Any]]) -> None:
            try:
                if result_future.cancelled():
                    return

                if f.cancelled():
                    result_future.cancel()
                    return

                if f.exception():
                    result_future.set_exception(f.exception())
                    return

                result = f.result()
                r = from_dict(result[0] if result and result[0] else {}, section)
                self._settings_cache[(scope, section.__config_section__)] = r
                result_future.set_result(r)
            except Exception as e:
                result_future.set_exception(e)

        self.get_configuration_raw(
            section=section.__config_section__,
            scope_uri=scope_uri,
        ).add_done_callback(_get_configuration_done)

        return result_future

    def get_configuration_raw(
        self,
        section: Optional[str],
        scope_uri: Union[str, Uri, None] = None,
    ) -> Task[Optional[Any]]:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.configuration
            and self.parent.running_thread != threading.current_thread()
        ):
            return self.parent.send_request(
                "workspace/configuration",
                ConfigurationParams(
                    items=[
                        ConfigurationItem(
                            scope_uri=str(scope_uri) if isinstance(scope_uri, Uri) else scope_uri,
                            section=section,
                        )
                    ]
                ),
                List[Any],
            )

        result = self.settings
        for sub_key in str(section).split("."):
            if sub_key in result:
                result = result.get(sub_key, None)
            else:
                result = {}
                break
        result_future: Task[Optional[Any]] = Task()
        result_future.set_result([result])
        return result_future

    @rpc_method(name="workspace/didChangeWorkspaceFolders", param_type=DidChangeWorkspaceFoldersParams)
    def _workspace_did_change_workspace_folders(
        self, event: WorkspaceFoldersChangeEvent, *args: Any, **kwargs: Any
    ) -> None:
        with self._workspace_folders_lock:
            to_remove: List[WorkspaceFolder] = []
            for removed in event.removed:
                to_remove += [w for w in self._workspace_folders if w.uri == removed.uri]

            for removed in event.added:
                to_remove += [w for w in self._workspace_folders if w.uri == removed.uri]

            for r in to_remove:
                self._workspace_folders.remove(r)

                settings_to_remove = [k for k in self._settings_cache.keys() if k[0] == r]
                for k in settings_to_remove:
                    self._settings_cache.pop(k, None)

            for a in event.added:
                self._workspace_folders.append(WorkspaceFolder(a.name, Uri(a.uri)))

        # TODO: do we need an event for this?

    @event
    def did_change_watched_files(sender, changes: List[FileEvent]) -> None: ...

    @rpc_method(name="workspace/didChangeWatchedFiles", param_type=DidChangeWatchedFilesParams, threaded=True)
    def _workspace_did_change_watched_files(self, changes: List[FileEvent], *args: Any, **kwargs: Any) -> None:
        changes = [e for e in changes if not e.uri.endswith("/globalStorage")]
        if changes:
            self.did_change_watched_files(self, changes)

    @_logger.call
    def add_file_watchers(
        self,
        callback: Callable[[Any, List[FileEvent]], None],
        watchers: List[Union[FileWatcher, str, Tuple[str, Optional[WatchKind]]]],
    ) -> FileWatcherEntry:
        with self._file_watchers_lock:
            _watchers = [
                e if isinstance(e, FileWatcher) else FileWatcher(*e) if isinstance(e, tuple) else FileWatcher(e)
                for e in watchers
            ]

            entry = FileWatcherEntry(id=str(uuid.uuid4()), callback=callback, watchers=_watchers)

            current_entry = next(
                (e for e in self._file_watchers if e.watchers == _watchers),
                None,
            )

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

                    def _done(f: Task[None]) -> None:
                        if f.cancelled():
                            return
                        exception = f.exception()
                        if exception is not None:
                            self._logger.exception(exception)

                    self.parent.register_capability(
                        entry.id,
                        "workspace/didChangeWatchedFiles",
                        DidChangeWatchedFilesRegistrationOptions(
                            watchers=[FileSystemWatcher(glob_pattern=w.glob_pattern, kind=w.kind) for w in _watchers]
                        ),
                    ).add_done_callback(_done)

                else:
                    # TODO: implement own filewatcher if not supported by language server client
                    self._logger.warning("client did not support workspace/didChangeWatchedFiles.")

            def remove() -> None:
                try:
                    self.remove_file_watcher_entry(entry)
                except RuntimeError:
                    pass

            weakref.finalize(entry, remove)

            self._file_watchers.add(entry)

            return entry

    @_logger.call
    def remove_file_watcher_entry(self, entry: FileWatcherEntry) -> None:
        with self._file_watchers_lock:
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
                    self.parent.unregister_capability(entry.id, "workspace/didChangeWatchedFiles")
                # TODO: implement own filewatcher if not supported by language server client

    def apply_edit(
        self, edit: WorkspaceEdit, label: Optional[str] = None, timeout: Optional[float] = None
    ) -> ApplyWorkspaceEditResult:
        if edit.changes:
            for uri, changes in edit.changes.items():
                if changes:
                    doc = self.parent.documents.get(uri)
                    for change in changes:
                        if doc is not None:
                            change.range = doc.range_to_utf16(change.range)
        if edit.document_changes:
            for doc_change in [v for v in edit.document_changes if isinstance(v, TextDocumentEdit)]:
                doc = self.parent.documents.get(doc_change.text_document.uri)
                if doc is not None:
                    for e in doc_change.edits:
                        e.range = doc.range_to_utf16(e.range)

        r = self.parent.send_request(
            "workspace/applyEdit",
            ApplyWorkspaceEditParams(edit, label),
            return_type=ApplyWorkspaceEditResult,
        ).result(timeout)

        assert r is not None

        return r
