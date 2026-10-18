import importlib
import threading
from concurrent.futures import CancelledError
from logging import CRITICAL
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from robotcode.core.concurrent import run_as_task
from robotcode.core.documents_manager import CantReadDocumentError
from robotcode.core.ignore_spec import (
    DEFAULT_SPEC_RULES,
    GIT_IGNORE_FILE,
    ROBOT_IGNORE_FILE,
    IgnoreSpec,
    iter_files,
    iter_files_includes,
)
from robotcode.core.language import language_id
from robotcode.core.lsp.types import DocumentUri, FileChangeType, FileEvent, WatchKind
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.path import probe_disk_info
from robotcode.core.workspace import WorkspaceFolder
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.parts.diagnostics import (
    AnalysisProgressMode,
    DiagnosticsMode,
)
from robotcode.language_server.robotframework.configuration import AnalysisConfig
from robotcode.robot.diagnostics.imports_manager import ImportsManager
from robotcode.robot.diagnostics.library_doc import (
    RESOURCE_FILE_EXTENSION,
    ROBOT_FILE_EXTENSION,
)

from ..configuration import RobotCodeConfig

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart

WORKSPACE_FILE_EXTENSIONS = [ROBOT_FILE_EXTENSION, RESOURCE_FILE_EXTENSION]
WORKSPACE_IGNORE_FILES = [ROBOT_IGNORE_FILE, GIT_IGNORE_FILE]


class RobotWorkspaceProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)
        self.parent.documents.on_read_document_text.add(self.on_read_document_text)
        self.parent.documents.did_create_uri.add(self._on_did_create_uri)
        self.parent.on_initialized.add(self._on_initialized)
        self.parent.diagnostics.on_workspace_loaded.add(self._on_workspace_loaded)
        self.parent.on_shutdown.add(self._stop_file_checks)
        self.parent.diagnostics.load_workspace_documents.add(self.load_workspace_documents)
        self.parent.diagnostics.on_get_diagnostics_mode.add(self.on_get_diagnostics_mode)
        self.parent.diagnostics.on_get_analysis_progress_mode.add(self.on_get_analysis_progress_mode)
        self.documents_loaded = Event()

        # the periodic check of the files of each workspace folder, by the folder's URI
        self._file_check_lock = threading.RLock()
        self._file_check_timers: Dict[str, threading.Timer] = {}
        self._file_checks_stopped = False

    def _on_initialized(self, sender: Any) -> None:
        # the workspace exists only after the initialize request, the parts of the protocol already before it
        self.parent.workspace.did_change_configuration.add(self._on_did_change_configuration)
        self.parent.workspace.add_file_watcher(
            self._on_files_deleted,
            f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
            WatchKind.DELETE,
        )

    def _on_files_deleted(self, sender: Any, changes: List[FileEvent]) -> None:
        for change in changes:
            if change.type != FileChangeType.DELETED:
                continue

            uri = Uri(change.uri).normalized()
            if uri.scheme != "file":
                continue

            path = uri.to_path()
            # the cache keeps the entries of a file that is there again
            if path.suffix in WORKSPACE_FILE_EXTENSIONS and not path.exists():
                self.parent.documents_cache.remove_cached_analysis(path)

    @language_id("robotframework")
    def on_read_document_text(self, sender: Any, uri: Uri) -> Optional[str]:
        from robot.utils import FileReader

        with FileReader(uri.to_path()) as reader:
            return str(reader.read())

    def on_get_diagnostics_mode(self, sender: Any, uri: Uri) -> Optional[DiagnosticsMode]:
        config = self.parent.workspace.get_configuration(AnalysisConfig, uri)
        return config.diagnostic_mode

    def on_get_analysis_progress_mode(self, sender: Any, uri: Uri) -> Optional[AnalysisProgressMode]:
        config = self.parent.workspace.get_configuration(AnalysisConfig, uri)
        return config.progress_mode

    def _exclude_spec(self, folder: WorkspaceFolder) -> IgnoreSpec:
        config = self.parent.workspace.get_configuration(RobotCodeConfig, folder.uri)
        exclude_patterns = [
            *self.parent.analysis_config.exclude_patterns,
            *(config.workspace.exclude_patterns or []),
        ]
        return IgnoreSpec.from_list([*DEFAULT_SPEC_RULES, *exclude_patterns], folder.uri.to_path())

    def collect_workspace_files(self, folder: WorkspaceFolder) -> List[Path]:
        """The Robot Framework files of a workspace folder, without the excluded and ignored ones."""
        return [
            f
            for f in iter_files(
                folder.uri.to_path(),
                ignore_files=WORKSPACE_IGNORE_FILES,
                include_hidden=False,
                parent_spec=self._exclude_spec(folder),
                verbose_callback=self._logger.debug,
                verbose_trace=False,
            )
            if f.suffix in WORKSPACE_FILE_EXTENSIONS
        ]

    def is_workspace_file(self, folder: WorkspaceFolder, path: Path) -> bool:
        """Whether `collect_workspace_files` would return `path`."""
        return path.suffix in WORKSPACE_FILE_EXTENSIONS and iter_files_includes(
            path,
            folder.uri.to_path(),
            ignore_files=WORKSPACE_IGNORE_FILES,
            include_hidden=False,
            parent_spec=self._exclude_spec(folder),
        )

    def _on_did_create_uri(self, sender: Any, uri: DocumentUri) -> None:
        # a created file is analyzed like the files found at startup
        file_uri = Uri(uri)
        if file_uri.scheme != "file":
            return

        path = file_uri.to_path()
        folder = self.parent.workspace.get_workspace_folder(file_uri)
        if folder is None or not self.is_workspace_file(folder, path):
            return

        try:
            document = self.parent.documents.get_or_open_document(path)
        except CantReadDocumentError as e:
            ex = e
            self._logger.debug(lambda: f"Can't load created document {path}: {ex}")
            return

        self.parent.diagnostics.force_refresh_document(document)

    def load_workspace_documents(self, sender: Any) -> None:
        with self._logger.measure_time(lambda: "loading workspace documents", context_name="load_workspace_documents"):
            try:
                for folder in self.parent.workspace.workspace_folders:
                    config = self.parent.workspace.get_configuration(RobotCodeConfig, folder.uri)

                    with self.parent.window.progress("Collect sources", cancellable=False):
                        files = self.collect_workspace_files(folder)

                    canceled = False
                    self._logger.debug(
                        lambda: f"Loading {len(files)} workspace documents", context_name="load_workspace_documents"
                    )
                    with self.parent.window.progress(
                        "Load workspace", current=0, max=len(files), start=False, cancellable=False
                    ) as progress:
                        for i, f in enumerate(files):
                            try:
                                self.parent.documents.get_or_open_document(f)

                                if config.analysis.progress_mode != AnalysisProgressMode.OFF:
                                    name = f.relative_to(folder.uri.to_path())

                                    progress.begin()
                                    progress.report(
                                        (
                                            f"Load {name!s}"
                                            if config.analysis.progress_mode == AnalysisProgressMode.DETAILED
                                            else None
                                        ),
                                        current=i,
                                    )
                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except CancelledError:
                                canceled = True
                                break
                            except BaseException as e:
                                ex = e
                                self._logger.exception(
                                    lambda: f"Can't load document {f}: {ex}",
                                    level=CRITICAL,
                                    context_name="load_workspace_documents",
                                )
            finally:
                if canceled:
                    self._logger.info(lambda: "Workspace loading canceled")

    def _documents_of(self, folder: WorkspaceFolder) -> List[TextDocument]:
        result = []
        for document in list(self.parent.documents.documents):
            document_folder = self.parent.workspace.get_workspace_folder(document.uri)
            if document_folder is not None and document_folder.uri == folder.uri:
                result.append(document)
        return result

    def check_workspace_folder(self, folder: WorkspaceFolder) -> None:
        """Find the changes of the files of a workspace folder, and handle them like the file events of the client."""
        changes: Dict[str, FileEvent] = {}

        def report(path: Path, change: FileChangeType) -> None:
            uri = str(Uri.from_path(path))
            if uri not in changes:
                changes[uri] = FileEvent(uri, change)

        for path in self.collect_workspace_files(folder):
            if self.parent.documents.get(Uri.from_path(path).normalized()) is None:
                report(path, FileChangeType.CREATED)

        # the documents open in the editor are the editor's
        for document in self._documents_of(folder):
            if document.opened_in_editor or document.uri.scheme != "file":
                continue

            path = document.uri.to_path()
            disk_info = probe_disk_info(path)
            if disk_info is None:
                report(path, FileChangeType.DELETED)
            elif disk_info != document.disk_info:
                report(path, FileChangeType.CHANGED)

        imports_manager = self.parent.documents_cache.get_imports_manager_for_workspace_folder(folder)
        for file in imports_manager.changed_import_files():
            report(Path(file), FileChangeType.CHANGED if Path(file).exists() else FileChangeType.DELETED)

        for file in self._found_failed_imports(folder, imports_manager):
            report(Path(file), FileChangeType.CREATED)

        if changes:
            self.parent.workspace.did_change_watched_files(self.parent.workspace, list(changes.values()))

    def _found_failed_imports(self, folder: WorkspaceFolder, imports_manager: ImportsManager) -> List[str]:
        """The files of the failed imports whose file or module was not found and is there now."""
        # a module created since the import failed is found only with fresh finder caches
        importlib.invalidate_caches()

        result: List[str] = []
        for document in self._documents_of(folder):
            namespace = self.parent.documents_cache.get_only_initialized_namespace(document)
            if namespace is None:
                continue

            for failed in namespace.failed_imports:
                if failed.found:
                    continue
                file = imports_manager.find_import_source(failed.imp, failed.base_dir, failed.variables)
                if file is not None:
                    result.append(file)
        return result

    def _on_workspace_loaded(self, sender: Any) -> None:
        self._schedule_file_checks()

    def _on_did_change_configuration(self, sender: Any, settings: Dict[str, Any]) -> None:
        # the interval of a folder may have changed; the configuration is read off the thread of the notification
        run_as_task(self._schedule_file_checks)

    def _schedule_file_checks(self) -> None:
        if self._file_checks_stopped or not self.parent.diagnostics.workspace_loaded_event.is_set():
            return

        for folder in self.parent.workspace.workspace_folders:
            self._schedule_file_check(folder)

    def _file_check_interval(self, folder: WorkspaceFolder) -> int:
        try:
            interval = self.parent.workspace.get_configuration(AnalysisConfig, folder.uri).file_check_interval
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            # without a timer the folder would not be checked again
            self._logger.exception(e)
            interval = AnalysisConfig().file_check_interval
        return min(max(interval, 1), 1440)

    def _schedule_file_check(self, folder: WorkspaceFolder) -> None:
        # reading the configuration can wait for the client, so it happens without the lock that the shutdown takes
        interval = self._file_check_interval(folder)

        with self._file_check_lock:
            if self._file_checks_stopped:
                return

            timer = self._file_check_timers.pop(str(folder.uri), None)
            if timer is not None:
                timer.cancel()

            timer = threading.Timer(interval * 60, self._run_file_check, (folder,))
            timer.daemon = True
            self._file_check_timers[str(folder.uri)] = timer
            timer.start()

    def _run_file_check(self, folder: WorkspaceFolder) -> None:
        try:
            self.check_workspace_folder(folder)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._logger.exception(e)
        finally:
            self._schedule_file_check(folder)

    def _stop_file_checks(self, sender: Any) -> None:
        with self._file_check_lock:
            self._file_checks_stopped = True
            for timer in self._file_check_timers.values():
                timer.cancel()
            self._file_check_timers.clear()

    @rpc_method(name="robot/cache/clear", threaded=True)
    def robot_cache_clear(self) -> None:
        for folder in self.parent.workspace.workspace_folders:
            self.parent.documents_cache.get_imports_manager_for_workspace_folder(folder).clear_cache()
