from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, List, Optional

from robotcode.jsonrpc2.protocol import rpc_method

from ....utils.async_tools import Event, threaded
from ....utils.glob_path import iter_files
from ....utils.logging import LoggingDescriptor
from ....utils.uri import InvalidUriError, Uri
from ...common.decorators import language_id
from ...common.lsp_types import FileChangeType, FileEvent, WatchKind
from ...common.parts.diagnostics import (
    AnalysisProgressMode,
    DiagnosticsMode,
    WorkspaceDocumentsResult,
)
from ..configuration import AnalysisConfig, RobotCodeConfig
from ..diagnostics.library_doc import RESOURCE_FILE_EXTENSION, ROBOT_FILE_EXTENSION

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class CantReadDocumentException(Exception):
    pass


class RobotWorkspaceProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)
        self.parent.documents.on_read_document_text.add(self._on_read_document_text)
        self.parent.diagnostics.load_workspace_documents.add(self._load_workspace_documents)
        self.parent.diagnostics.on_get_diagnostics_mode.add(self.on_get_diagnostics_mode)
        self.parent.diagnostics.on_get_analysis_progress_mode.add(self.on_get_analysis_progress_mode)
        self.parent.on_initialized.add(self.on_initialized)
        self.documents_loaded = Event()

    async def on_initialized(self, sender: Any) -> None:
        await self.parent.workspace.add_file_watcher(
            self.on_file_changed, f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}", WatchKind.CREATE
        )

    async def on_file_changed(self, sender: Any, files: List[FileEvent]) -> None:  #
        for fe in [f for f in files if f.type == FileChangeType.CREATED]:
            doc_uri = Uri(fe.uri)
            try:
                path = doc_uri.to_path()
                if path.suffix in [ROBOT_FILE_EXTENSION, RESOURCE_FILE_EXTENSION]:
                    document = await self.parent.documents.get_or_open_document(path)
                    if not document.opened_in_editor:
                        await (await self.parent.documents_cache.get_namespace(document)).ensure_initialized()

            except InvalidUriError:
                pass

    @language_id("robotframework")
    async def _on_read_document_text(self, sender: Any, uri: Uri) -> Optional[str]:
        from robot.utils import FileReader

        with FileReader(uri.to_path()) as reader:
            return str(reader.read())

    async def on_get_diagnostics_mode(self, sender: Any, uri: Uri) -> Optional[DiagnosticsMode]:
        config = await self.parent.workspace.get_configuration(AnalysisConfig, uri)
        return config.diagnostic_mode

    async def on_get_analysis_progress_mode(self, sender: Any, uri: Uri) -> Optional[AnalysisProgressMode]:
        config = await self.parent.workspace.get_configuration(AnalysisConfig, uri)
        return config.progress_mode

    @threaded()
    async def _load_workspace_documents(self, sender: Any) -> List[WorkspaceDocumentsResult]:
        start = time.monotonic()
        try:

            result: List[WorkspaceDocumentsResult] = []

            for folder in self.parent.workspace.workspace_folders:
                config = await self.parent.workspace.get_configuration(RobotCodeConfig, folder.uri)

                async with self.parent.window.progress("Collect sources", cancellable=False):
                    files = [
                        f
                        for f in iter_files(
                            folder.uri.to_path(),
                            f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
                            ignore_patterns=config.workspace.exclude_patterns or [],
                            absolute=True,
                        )
                    ]

                canceled = False
                async with self.parent.window.progress(
                    "Load workspace", cancellable=True, current=0, max=len(files), start=False
                ) as progress:
                    try:
                        for i, f in enumerate(files):
                            try:
                                await self.parent.documents.get_or_open_document(f)

                                if config.analysis.progress_mode != AnalysisProgressMode.OFF:
                                    name = f.relative_to(folder.uri.to_path())

                                    progress.begin()
                                    progress.report(
                                        f"Load {str(name)}"
                                        if config.analysis.progress_mode == AnalysisProgressMode.DETAILED
                                        else None,
                                        current=i,
                                    )
                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException as e:
                                self._logger.critical(f"Can't load document {f}: {e}")
                    finally:
                        self.documents_loaded.set()

                    for i, f in enumerate(files):
                        try:
                            if progress.is_canceled:
                                canceled = True
                                break

                            name = f.relative_to(folder.uri.to_path())

                            if config.analysis.progress_mode != AnalysisProgressMode.OFF:
                                progress.begin()
                                progress.report(
                                    f"Initialize {str(name)}"
                                    if config.analysis.progress_mode == AnalysisProgressMode.DETAILED
                                    else None,
                                    current=i,
                                )

                            if not f.exists():
                                continue

                            document = await self.parent.documents.get_or_open_document(f, "robotframework")

                            if not document.opened_in_editor:
                                await (await self.parent.documents_cache.get_namespace(document)).ensure_initialized()

                                if config.analysis.diagnostic_mode == DiagnosticsMode.WORKSPACE:
                                    result.append(
                                        WorkspaceDocumentsResult(
                                            str(name)
                                            if config.analysis.progress_mode == AnalysisProgressMode.DETAILED
                                            else None,
                                            document,
                                        )
                                    )

                        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                            raise
                        except BaseException as e:
                            self._logger.critical(f"Can't initialize document {f}: {e}")

            if canceled:
                return []

            if config.analysis.max_project_file_count > 0 and len(files) > config.analysis.max_project_file_count:
                result = result[: config.analysis.max_project_file_count]

            return result
        finally:
            self._logger.info(f"Workspace loaded {len(result)} documents in {time.monotonic() - start}s")

    @rpc_method(name="robot/cache/clear")
    @threaded()
    async def get_tests_from_workspace(self) -> None:
        for folder in self.parent.workspace.workspace_folders:
            (await self.parent.documents_cache.get_imports_manager_for_workspace_folder(folder)).clear_cache()
