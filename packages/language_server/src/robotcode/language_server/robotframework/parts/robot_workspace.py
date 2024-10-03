from concurrent.futures import CancelledError
from logging import CRITICAL
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Any, List, Optional

from robotcode.core.ignore_spec import DEFAULT_SPEC_RULES, GIT_IGNORE_FILE, ROBOT_IGNORE_FILE, IgnoreSpec, iter_files
from robotcode.core.language import language_id
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.language_server.common.parts.diagnostics import (
    AnalysisProgressMode,
    DiagnosticsMode,
)
from robotcode.language_server.robotframework.configuration import AnalysisConfig
from robotcode.robot.diagnostics.library_doc import (
    RESOURCE_FILE_EXTENSION,
    ROBOT_FILE_EXTENSION,
)

from ..configuration import RobotCodeConfig

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

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
        self.documents_loaded = Event()

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

    def load_workspace_documents(self, sender: Any) -> None:
        with self._logger.measure_time(lambda: "loading workspace documents", context_name="load_workspace_documents"):
            try:
                result: List[Path] = []

                for folder in self.parent.workspace.workspace_folders:
                    config = self.parent.workspace.get_configuration(RobotCodeConfig, folder.uri)

                    extensions = [ROBOT_FILE_EXTENSION, RESOURCE_FILE_EXTENSION]
                    with self.parent.window.progress("Collect sources", cancellable=False):
                        files = list(
                            filter(
                                lambda f: f.suffix in extensions,
                                iter_files(
                                    folder.uri.to_path(),
                                    ignore_files=[ROBOT_IGNORE_FILE, GIT_IGNORE_FILE],
                                    include_hidden=False,
                                    parent_spec=IgnoreSpec.from_list(
                                        [*DEFAULT_SPEC_RULES, *(config.workspace.exclude_patterns or [])],
                                        folder.uri.to_path(),
                                    ),
                                    verbose_callback=self._logger.debug,
                                    verbose_trace=False,
                                ),
                            )
                        )

                    result.extend(files)

                    canceled = False
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

    @rpc_method(name="robot/cache/clear", threaded=True)
    def robot_cache_clear(self) -> None:
        for folder in self.parent.workspace.workspace_folders:
            self.parent.documents_cache.get_imports_manager_for_workspace_folder(folder).clear_cache()
