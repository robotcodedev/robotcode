from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, List, Optional

from ....utils.async_tools import Event, threaded
from ....utils.glob_path import iter_files
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.decorators import language_id
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
        self.workspace_loaded = Event()

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

        result: List[WorkspaceDocumentsResult] = []

        for folder in self.parent.workspace.workspace_folders:
            config = await self.parent.workspace.get_configuration(RobotCodeConfig, folder.uri)

            async with self.parent.window.progress("Collect sources", cancellable=False):
                files = [
                    f
                    async for f in iter_files(
                        folder.uri.to_path(),
                        f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
                        ignore_patterns=config.workspace.exclude_patterns or [],  # type: ignore
                        absolute=True,
                    )
                ]

            canceled = False
            async with self.parent.window.progress(
                "Load workspace", cancellable=True, current=0, max=len(files)
            ) as progress:
                for i, f in enumerate(files):
                    try:
                        if progress.is_canceled:
                            canceled = True
                            break

                        name = f.relative_to(folder.uri.to_path())

                        progress.report(
                            f"Load {str(name)}"
                            if config.analysis.progress_mode == AnalysisProgressMode.DETAILED
                            else None,
                            current=i,
                        )

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
                        self._logger.exception(e)

        self.workspace_loaded.set()

        if canceled:
            return []

        if config.analysis.max_project_file_count > 0 and len(files) > config.analysis.max_project_file_count:
            result = result[: config.analysis.max_project_file_count]

        return result
