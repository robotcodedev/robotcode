import time
from threading import Event
from typing import TYPE_CHECKING, Any, List, Optional

from robotcode.core.lsp.types import FileChangeType, FileEvent, WatchKind
from robotcode.core.uri import InvalidUriError, Uri
from robotcode.core.utils.glob_path import iter_files
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.decorators import language_id
from robotcode.language_server.common.parts.diagnostics import (
    AnalysisProgressMode,
    DiagnosticsMode,
    WorkspaceDocumentsResult,
)
from robotcode.language_server.robotframework.configuration import (
    AnalysisConfig,
    RobotCodeConfig,
)
from robotcode.robot.diagnostics.library_doc import (
    RESOURCE_FILE_EXTENSION,
    ROBOT_FILE_EXTENSION,
)

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import (
        RobotLanguageServerProtocol,
    )

from .protocol_part import RobotLanguageServerProtocolPart


class CantReadDocumentError(Exception):
    pass


class RobotWorkspaceProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)
        self.parent.documents.on_read_document_text.add(self.on_read_document_text)
        self.parent.diagnostics.load_workspace_documents.add(self.load_workspace_documents)
        self.parent.diagnostics.on_get_diagnostics_mode.add(self.on_get_diagnostics_mode)
        self.parent.diagnostics.on_get_analysis_progress_mode.add(self.on_get_analysis_progress_mode)
        self.parent.on_initialized.add(self.server_initialized)
        self.documents_loaded = Event()

    def server_initialized(self, sender: Any) -> None:
        self.parent.workspace.add_file_watcher(
            self.on_file_changed,
            f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
            WatchKind.CREATE,
        )

    def on_file_changed(self, sender: Any, files: List[FileEvent]) -> None:  #
        for fe in [f for f in files if f.type == FileChangeType.CREATED]:
            doc_uri = Uri(fe.uri)
            try:
                path = doc_uri.to_path()
                if path.suffix in [
                    ROBOT_FILE_EXTENSION,
                    RESOURCE_FILE_EXTENSION,
                ]:
                    document = self.parent.documents.get_or_open_document(path)
                    if not document.opened_in_editor:
                        self.parent.documents_cache.get_namespace(document).ensure_initialized()

            except InvalidUriError:
                pass

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

    def load_workspace_documents(self, sender: Any) -> List[WorkspaceDocumentsResult]:
        start = time.monotonic()
        try:
            result: List[WorkspaceDocumentsResult] = []

            for folder in self.parent.workspace.workspace_folders:
                config = self.parent.workspace.get_configuration(RobotCodeConfig, folder.uri)

                with self.parent.window.progress("Collect sources", cancellable=False):
                    files = list(
                        iter_files(
                            folder.uri.to_path(),
                            f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
                            ignore_patterns=config.workspace.exclude_patterns or [],
                            absolute=True,
                        )
                    )

                canceled = False
                with self.parent.window.progress(
                    "Load workspace", current=0, max=len(files), start=False, cancellable=False
                ) as progress:
                    try:
                        for i, f in enumerate(files):
                            try:
                                self.parent.documents.get_or_open_document(f)

                                if config.analysis.progress_mode != AnalysisProgressMode.OFF:
                                    name = f.relative_to(folder.uri.to_path())

                                    progress.begin()
                                    progress.report(
                                        f"Load {name!s}"
                                        if config.analysis.progress_mode == AnalysisProgressMode.DETAILED
                                        else None,
                                        current=i,
                                    )
                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException as e:
                                ex = e
                                self._logger.critical(lambda: f"Can't load document {f}: {ex}")
                    finally:
                        self.documents_loaded.set()

            if canceled:
                return []

            if config.analysis.max_project_file_count > 0 and len(files) > config.analysis.max_project_file_count:
                result = result[: config.analysis.max_project_file_count]

            return result
        finally:
            self._logger.info(lambda: f"Workspace loaded {len(result)} documents in {time.monotonic() - start}s")

    @rpc_method(name="robot/cache/clear", threaded=True)
    def robot_cache_clear(self) -> None:
        for folder in self.parent.workspace.workspace_folders:
            self.parent.documents_cache.get_imports_manager_for_workspace_folder(folder).clear_cache()
