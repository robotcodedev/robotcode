from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from ....jsonrpc2.protocol import JsonRPCErrorException, rpc_method
from ....utils.async_tools import (
    Event,
    Lock,
    async_event,
    async_tasking_event,
    async_tasking_event_iterator,
    create_sub_task,
    threaded,
)
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ..decorators import language_id_filter
from ..has_extend_capabilities import HasExtendCapabilities
from ..lsp_types import (
    Diagnostic,
    DiagnosticOptions,
    DiagnosticServerCancellationData,
    DocumentDiagnosticParams,
    DocumentDiagnosticReport,
    ErrorCodes,
    PreviousResultId,
    ProgressToken,
    RelatedFullDocumentDiagnosticReport,
    RelatedUnchangedDocumentDiagnosticReport,
    ServerCapabilities,
    TextDocumentIdentifier,
    WorkspaceDiagnosticParams,
    WorkspaceDiagnosticReport,
    WorkspaceDiagnosticReportPartialResult,
    WorkspaceDocumentDiagnosticReport,
    WorkspaceFullDocumentDiagnosticReport,
    WorkspaceUnchangedDocumentDiagnosticReport,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart

__all__ = ["DiagnosticsProtocolPart", "DiagnosticsResult"]


class DiagnosticsMode(Enum):
    WORKSPACE = "workspace"
    OPENFILESONLY = "openFilesOnly"


class AnalysisProgressMode(Enum):
    SIMPLE = "simple"
    DETAILED = "detailed"


WORKSPACE_URI = Uri("workspace:/")


@dataclass
class DiagnosticsResult:
    key: Any
    diagnostics: Optional[List[Diagnostic]] = None


@dataclass
class WorkspaceDocumentsResult:
    name: Optional[str]
    document: TextDocument


class DiagnosticsProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger = LoggingDescriptor()

    def __init__(self, protocol: LanguageServerProtocol) -> None:
        super().__init__(protocol)

        self.workspace_loaded_event = Event()

        self._workspace_load_lock = Lock()
        self._workspace_loaded = False

        self._current_document_tasks: Dict[
            TextDocument, asyncio.Task[Optional[RelatedFullDocumentDiagnosticReport]]
        ] = {}

        self._current_workspace_task: Optional[asyncio.Task[WorkspaceDiagnosticReport]] = None

        self.in_get_workspace_diagnostics = Event(True)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.text_document is not None
            and self.parent.client_capabilities.text_document.diagnostic is not None
        ):
            capabilities.diagnostic_provider = DiagnosticOptions(
                inter_file_dependencies=True,
                workspace_diagnostics=True,
                identifier=f"robotcodelsp_{uuid.uuid4()}",
                work_done_progress=True,
            )

    @async_tasking_event_iterator
    async def collect(sender, document: TextDocument) -> DiagnosticsResult:  # NOSONAR
        ...

    @async_tasking_event
    async def load_workspace_documents(sender) -> List[WorkspaceDocumentsResult]:  # NOSONAR
        ...

    @async_tasking_event
    async def on_workspace_loaded(sender) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def on_workspace_diagnostics_ended(sender) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def on_document_diagnostics_ended(sender) -> None:  # NOSONAR
        ...

    @async_event
    async def on_get_analysis_progress_mode(sender, uri: Uri) -> Optional[AnalysisProgressMode]:  # NOSONAR
        ...

    @async_event
    async def on_get_diagnostics_mode(sender, uri: Uri) -> Optional[DiagnosticsMode]:  # NOSONAR
        ...

    async def ensure_workspace_loaded(self) -> None:
        if not self._workspace_loaded:
            async with self._workspace_load_lock:
                if not self._workspace_loaded:
                    if self.workspace_loaded_event.is_set():
                        return

                    try:
                        await self.load_workspace_documents(self)
                    finally:
                        self._workspace_loaded = True
                        self.workspace_loaded_event.set()
                        await self.on_workspace_loaded(self)

    async def get_document_diagnostics(self, document: TextDocument) -> RelatedFullDocumentDiagnosticReport:
        return await document.get_cache(self.__get_document_diagnostics)

    async def __get_document_diagnostics(self, document: TextDocument) -> RelatedFullDocumentDiagnosticReport:
        await self.ensure_workspace_loaded()

        diagnostics: List[Diagnostic] = []

        async for result_any in self.collect(
            self, document, callback_filter=language_id_filter(document), return_exceptions=True
        ):
            result = cast(DiagnosticsResult, result_any)

            if isinstance(result, BaseException):
                if not isinstance(result, asyncio.CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:
                diagnostics.extend(result.diagnostics or [])

        return RelatedFullDocumentDiagnosticReport(items=diagnostics, result_id=str(uuid.uuid4()))

    @rpc_method(name="textDocument/diagnostic", param_type=DocumentDiagnosticParams)
    @threaded()
    async def _text_document_diagnostic(
        self,
        text_document: TextDocumentIdentifier,
        identifier: Optional[str],
        previous_result_id: Optional[str],
        *args: Any,
        **kwargs: Any,
    ) -> DocumentDiagnosticReport:
        self._logger.debug(lambda: f"textDocument/diagnostic for {text_document}")

        try:
            document = await self.parent.documents.get(text_document.uri)
            if document is None:
                raise JsonRPCErrorException(ErrorCodes.INVALID_PARAMS, f"Document {text_document!r} not found")

            async def _get_diagnostics(doc: TextDocument) -> Optional[RelatedFullDocumentDiagnosticReport]:
                if document is not None:
                    return await self.get_document_diagnostics(doc)

                return None

            if document in self._current_document_tasks and not self._current_document_tasks[document].done():
                self._logger.debug(lambda: f"textDocument/diagnostic cancel old task {text_document}")
                self._current_document_tasks[document].cancel()

            task = create_sub_task(_get_diagnostics(document))
            self._current_document_tasks[document] = task

            try:
                result = await task
                if result is None:
                    raise RuntimeError("Unexpected result.")

            except asyncio.CancelledError:
                self._logger.debug(lambda: f"textDocument/diagnostic canceled {text_document}")
                raise
            finally:
                if document in self._current_document_tasks and self._current_document_tasks[document] == task:
                    del self._current_document_tasks[document]

            if result.result_id is not None and result.result_id == previous_result_id:
                return RelatedUnchangedDocumentDiagnosticReport(result_id=result.result_id)

            return result
        finally:

            await self.on_document_diagnostics_ended(self)

            self._logger.debug(lambda: f"textDocument/diagnostic ready  {text_document}")

    @rpc_method(name="workspace/diagnostic", param_type=WorkspaceDiagnosticParams)
    @threaded()
    async def _workspace_diagnostic(
        self,
        identifier: Optional[str],
        previous_result_ids: List[PreviousResultId],
        partial_result_token: Optional[ProgressToken],
        work_done_token: Optional[ProgressToken] = None,
        *args: Any,
        **kwargs: Any,
    ) -> WorkspaceDiagnosticReport:
        self._logger.debug("workspace/diagnostic")

        async def _get_diagnostics() -> WorkspaceDiagnosticReport:
            result: List[WorkspaceDocumentDiagnosticReport] = []

            for doc in self.parent.documents.documents:
                doc_result = await self.get_document_diagnostics(doc)

                if doc_result.result_id is not None and any(
                    p
                    for p in previous_result_ids
                    if p.value == doc_result.result_id and Uri(p.uri).normalized() == doc.uri
                ):
                    result.append(
                        WorkspaceUnchangedDocumentDiagnosticReport(doc.document_uri, doc.version, doc_result.result_id)
                    )
                else:
                    result.append(
                        WorkspaceFullDocumentDiagnosticReport(
                            doc.document_uri, doc.version, doc_result.items, doc_result.result_id
                        )
                    )
            return WorkspaceDiagnosticReport(items=result)

        async def _get_partial_diagnostics() -> WorkspaceDiagnosticReport:
            async with self.parent.window.progress(
                "Analyse Workspace",
                progress_token=work_done_token,
                cancellable=False,
            ) as progress:

                async def _task(doc: TextDocument) -> None:
                    if doc.opened_in_editor:
                        return

                    if await self.get_analysis_progress_mode(doc.uri) == AnalysisProgressMode.DETAILED:
                        path = doc.uri.to_path()
                        folder = self.parent.workspace.get_workspace_folder(doc.uri)
                        if folder is None:
                            name = path
                        else:
                            name = path.relative_to(folder.uri.to_path())

                        progress.report(f"Analyse {name}")

                    doc_result = await self.get_document_diagnostics(doc)

                    if doc_result.result_id is not None and any(
                        p
                        for p in previous_result_ids
                        if p.value == doc_result.result_id and Uri(p.uri).normalized() == doc.uri
                    ):
                        self.parent.window.send_progress(
                            partial_result_token,
                            WorkspaceDiagnosticReportPartialResult(
                                [
                                    WorkspaceUnchangedDocumentDiagnosticReport(
                                        doc.document_uri, doc.version, doc_result.result_id
                                    )
                                ]
                            ),
                        )
                    else:
                        self.parent.window.send_progress(
                            partial_result_token,
                            WorkspaceDiagnosticReportPartialResult(
                                [
                                    WorkspaceFullDocumentDiagnosticReport(
                                        doc.document_uri, doc.version, doc_result.items, doc_result.result_id
                                    )
                                ]
                            ),
                        )

                for doc in self.parent.documents.documents:
                    if await self.get_diagnostics_mode(doc.uri) == DiagnosticsMode.WORKSPACE:
                        await _task(doc)

                return WorkspaceDiagnosticReport(items=[])

        self.in_get_workspace_diagnostics.clear()
        try:
            await self.ensure_workspace_loaded()

            if self._current_workspace_task is not None:
                self._current_workspace_task.cancel()

            task = create_sub_task(_get_diagnostics() if partial_result_token is None else _get_partial_diagnostics())
            self._current_workspace_task = task
            try:
                return await task
            except asyncio.CancelledError:
                self._logger.debug("workspace/diagnostic canceled")
                if self._current_workspace_task is None:
                    raise JsonRPCErrorException(
                        ErrorCodes.SERVER_CANCELLED,
                        "ServerCancelled",
                        data=DiagnosticServerCancellationData(True),
                    )
                raise
            finally:
                if self._current_workspace_task == task:
                    self._current_workspace_task = None
                self._logger.debug("workspace/diagnostic ready")
        finally:
            self.in_get_workspace_diagnostics.set()
            await self.on_workspace_diagnostics_ended(self)

    async def cancel_workspace_diagnostics(self) -> None:
        if self._current_workspace_task is not None and not self._current_workspace_task.done():
            task = self._current_workspace_task
            self._current_workspace_task = None
            task.get_loop().call_soon_threadsafe(task.cancel)

    async def cancel_document_diagnostics(self, document: TextDocument) -> None:
        task = self._current_document_tasks.get(document, None)
        if task is not None:
            self._logger.critical(lambda: f"textDocument/diagnostic canceled {document}")
            task.get_loop().call_soon_threadsafe(task.cancel)

    async def get_analysis_progress_mode(self, uri: Uri) -> AnalysisProgressMode:
        for e in await self.on_get_analysis_progress_mode(self, uri):
            if e is not None:
                return cast(AnalysisProgressMode, e)

        return AnalysisProgressMode.SIMPLE

    async def get_diagnostics_mode(self, uri: Uri) -> DiagnosticsMode:
        for e in await self.on_get_diagnostics_mode(self, uri):
            if e is not None:
                return cast(DiagnosticsMode, e)

        return DiagnosticsMode.OPENFILESONLY

    async def refresh(self) -> None:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.diagnostics
            and self.parent.client_capabilities.workspace.diagnostics.refresh_support
        ):
            await self.parent.send_request_async("workspace/diagnostic/refresh")
