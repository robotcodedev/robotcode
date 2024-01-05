import itertools
import time
import uuid
from concurrent.futures import CancelledError
from dataclasses import dataclass, field
from enum import Enum
from threading import Event, RLock
from typing import TYPE_CHECKING, Any, Dict, Final, List, Optional, cast

from robotcode.core.concurrent import (
    FutureEx,
    check_current_thread_canceled,
    run_in_thread,
    threaded,
)
from robotcode.core.event import event
from robotcode.core.lsp.types import (
    Diagnostic,
    DiagnosticOptions,
    DiagnosticServerCancellationData,
    DocumentDiagnosticParams,
    DocumentDiagnosticReport,
    LSPErrorCodes,
    PreviousResultId,
    ProgressToken,
    PublishDiagnosticsParams,
    RelatedFullDocumentDiagnosticReport,
    ServerCapabilities,
    TextDocumentIdentifier,
    WorkspaceDiagnosticParams,
    WorkspaceDiagnosticReport,
)
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import JsonRPCErrorException, rpc_method
from robotcode.language_server.common.decorators import language_id_filter
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol

__all__ = ["DiagnosticsProtocolPart", "DiagnosticsResult"]


class DiagnosticsMode(Enum):
    OFF = "off"
    WORKSPACE = "workspace"
    OPENFILESONLY = "openFilesOnly"


class AnalysisProgressMode(Enum):
    OFF = "off"
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


@dataclass
class DiagnosticsData:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entries: Dict[Any, Optional[List[Diagnostic]]] = field(default_factory=dict)
    version: Optional[int] = None
    future: Optional[FutureEx[Any]] = None
    force: bool = False


class DiagnosticsProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, protocol: "LanguageServerProtocol") -> None:
        super().__init__(protocol)

        self.workspace_loaded_event = Event()

        self._workspace_load_lock = RLock()
        self._workspace_loaded = False

        self._workspace_diagnostics_task: Optional[FutureEx[Any]] = None

        self.parent.on_initialized.add(self.server_initialized)

        self.parent.on_exit.add(self.cancel_workspace_diagnostics_task)

        self.parent.documents.did_close.add(self.on_did_close)

        self.in_get_workspace_diagnostics = Event()
        self.in_get_workspace_diagnostics

        self.refresh_task: Optional[FutureEx[Any]] = None

        self.client_supports_pull = False

        self._refresh_timeout = 5

    def server_initialized(self, sender: Any) -> None:
        self._workspace_diagnostics_task = run_in_thread(self.run_workspace_diagnostics)

        if not self.client_supports_pull:
            self.parent.documents.did_open.add(self.update_document_diagnostics)
            self.parent.documents.did_change.add(self.update_document_diagnostics)
            self.parent.documents.did_save.add(self.update_document_diagnostics)

    def extend_capabilities(self, capabilities: ServerCapabilities) -> None:
        if (
            self.parent.client_capabilities is not None
            and self.parent.client_capabilities.text_document is not None
            and self.parent.client_capabilities.text_document.diagnostic is not None
        ):
            capabilities.diagnostic_provider = DiagnosticOptions(
                inter_file_dependencies=True,
                workspace_diagnostics=False,
                identifier=f"robotcodelsp_{uuid.uuid4()}",
                work_done_progress=True,
            )
            self.client_supports_pull = True

    @event
    def collect(sender, document: TextDocument) -> Optional[DiagnosticsResult]:  # NOSONAR
        ...

    @event
    def load_workspace_documents(
        sender,
    ) -> Optional[List[WorkspaceDocumentsResult]]:  # NOSONAR
        ...

    @event
    def on_workspace_loaded(sender) -> None:  # NOSONAR
        ...

    @event
    def on_get_analysis_progress_mode(sender, uri: Uri) -> Optional[AnalysisProgressMode]:  # NOSONAR
        ...

    @event
    def on_get_diagnostics_mode(sender, uri: Uri) -> Optional[DiagnosticsMode]:  # NOSONAR
        ...

    def ensure_workspace_loaded(self) -> None:
        with self._workspace_load_lock:
            if not self._workspace_loaded and not self.workspace_loaded_event.is_set():
                self._logger.debug("load workspace documents")
                try:
                    self.load_workspace_documents(self)
                finally:
                    self._workspace_loaded = True
                    self.workspace_loaded_event.set()
                    self.on_workspace_loaded(self)
                    self.force_refresh_all()

    def force_refresh_all(self, refresh: bool = True) -> None:
        for doc in self.parent.documents.documents:
            self.get_diagnostics_data(doc).force = True

        if refresh:
            self.refresh()

    def force_refresh_document(self, document: TextDocument, refresh: bool = True) -> None:
        self.get_diagnostics_data(document).force = True
        if refresh and document.opened_in_editor:
            self.refresh()

    @_logger.call
    @threaded
    def on_did_close(self, sender: Any, document: TextDocument) -> None:
        run_in_thread(self._close_diagnostics_for_document, document)

    def _close_diagnostics_for_document(self, document: TextDocument) -> None:
        if self.get_diagnostics_mode(document.uri) == DiagnosticsMode.WORKSPACE:
            return

        try:
            data = self.get_diagnostics_data(document)
            if data.future is not None and not data.future.done():
                self._logger.debug(lambda: f"try to cancel diagnostics for {document}")

                data.future.cancel()
        finally:
            self.publish_diagnostics(document, diagnostics=[])

    def cancel_workspace_diagnostics_task(self, sender: Any) -> None:
        if self._workspace_diagnostics_task is not None:
            self._workspace_diagnostics_task.cancel()

    @_logger.call
    def run_workspace_diagnostics(self) -> None:
        self._logger.debug("start workspace diagnostics loop")
        self.ensure_workspace_loaded()

        while True:
            check_current_thread_canceled()

            try:
                documents = [
                    doc
                    for doc in self.parent.documents.documents
                    if not doc.opened_in_editor
                    and (
                        (data := self.get_diagnostics_data(doc)).force
                        or doc.version != data.version
                        or data.future is None
                    )
                ]

                if len(documents) == 0:
                    check_current_thread_canceled(1)
                    continue

                self._logger.info(lambda: f"start collecting workspace diagnostics for {len(documents)} documents")

                done_something = False

                start = time.monotonic()
                with self.parent.window.progress(
                    "Analyse workspace",
                    cancellable=False,
                    current=0,
                    max=len(documents) + 1,
                    start=False,
                ) as progress:
                    for i, document in enumerate(documents):
                        check_current_thread_canceled()

                        mode = self.get_diagnostics_mode(document.uri)
                        if mode == DiagnosticsMode.OFF:
                            self.get_diagnostics_data(document).version = document.version
                            continue

                        if document.opened_in_editor:
                            continue

                        done_something = True

                        analysis_mode = self.get_analysis_progress_mode(document.uri)

                        if analysis_mode == AnalysisProgressMode.DETAILED:
                            progress.begin()
                            path = document.uri.to_path()
                            folder = self.parent.workspace.get_workspace_folder(document.uri)
                            name = path if folder is None else path.relative_to(folder.uri.to_path())

                            progress.report(f"Analyse {name}", current=i + 1)
                        elif analysis_mode == AnalysisProgressMode.SIMPLE:
                            progress.begin()
                            progress.report(current=i + 1)

                        self.create_document_diagnostics_task(
                            document,
                            False,
                            False,
                            mode == DiagnosticsMode.WORKSPACE,
                        )

                if not done_something:
                    check_current_thread_canceled(1)

                self._logger.info(
                    lambda: f"collecting workspace diagnostics for {len(documents)} "
                    f"documents takes {time.monotonic() - start}s"
                )

            except (SystemExit, KeyboardInterrupt, CancelledError):
                raise
            except BaseException as e:
                ex = e
                self._logger.exception(
                    lambda: f"Error in workspace diagnostics loop: {ex}",
                    exc_info=e,
                )

    def create_document_diagnostics_task(
        self,
        document: TextDocument,
        single: bool,
        debounce: bool = True,
        send_diagnostics: bool = True,
    ) -> FutureEx[Any]:
        def done(t: FutureEx[Any]) -> None:
            self._logger.debug(lambda: f"diagnostics for {document} {'canceled' if t.cancelled() else 'ended'}")

        data = self.get_diagnostics_data(document)

        if data.force or document.version != data.version or data.future is None:
            future = data.future

            data.force = False

            if future is not None and not future.done():
                self._logger.debug(lambda: f"try to cancel diagnostics for {document}")

                future.cancel()

            data.version = document.version
            data.future = run_in_thread(
                self._get_diagnostics_for_document,
                document,
                data,
                debounce,
                send_diagnostics,
            )

            data.future.add_done_callback(done)

        return data.future

    @_logger.call
    def _get_diagnostics_for_document(
        self,
        document: TextDocument,
        data: DiagnosticsData,
        debounce: bool = True,
        send_diagnostics: bool = True,
    ) -> None:
        self._logger.debug(lambda: f"Get diagnostics for {document}")

        if debounce:
            check_current_thread_canceled(0.75)

        collected_keys: List[Any] = []
        try:
            for result in self.collect(
                self,
                document,
                callback_filter=language_id_filter(document),
                return_exceptions=True,
            ):
                check_current_thread_canceled()

                if isinstance(result, BaseException):
                    if not isinstance(result, CancelledError):
                        self._logger.exception(result, exc_info=result)
                    continue
                if result is None:
                    continue

                data.id = str(uuid.uuid4())

                if result.diagnostics is not None:
                    for d in result.diagnostics:
                        d.range = document.range_to_utf16(d.range)

                        for r in d.related_information or []:
                            doc = self.parent.documents.get(r.location.uri)
                            if doc is not None:
                                r.location.range = doc.range_to_utf16(r.location.range)

                data.entries[result.key] = result.diagnostics
                if result.diagnostics is not None:
                    collected_keys.append(result.key)

                if data.entries and send_diagnostics:
                    self.publish_diagnostics(
                        document,
                        diagnostics=[l for l in itertools.chain(*[i for i in data.entries.values() if i is not None])],
                    )

        except CancelledError:
            self._logger.debug(lambda: f"_get_diagnostics cancelled for {document}")
        finally:
            for k in set(data.entries.keys()) - set(collected_keys):
                data.entries.pop(k)

    def publish_diagnostics(self, document: TextDocument, diagnostics: List[Diagnostic]) -> None:
        self.parent.send_notification(
            "textDocument/publishDiagnostics",
            PublishDiagnosticsParams(
                uri=document.document_uri,
                version=document.version,
                diagnostics=diagnostics,
            ),
        )

    def update_document_diagnostics(self, sender: Any, document: TextDocument) -> None:
        self.create_document_diagnostics_task(document, True)

    @rpc_method(name="textDocument/diagnostic", param_type=DocumentDiagnosticParams, threaded=True)
    def _text_document_diagnostic(
        self,
        text_document: TextDocumentIdentifier,
        identifier: Optional[str],
        previous_result_id: Optional[str],
        *args: Any,
        **kwargs: Any,
    ) -> DocumentDiagnosticReport:
        try:
            if not self.parent.is_initialized.is_set():
                raise JsonRPCErrorException(
                    LSPErrorCodes.SERVER_CANCELLED,
                    "Server not initialized.",
                    DiagnosticServerCancellationData(True),
                )

            document = self.parent.documents.get(text_document.uri)
            if document is None:
                raise JsonRPCErrorException(
                    LSPErrorCodes.SERVER_CANCELLED,
                    f"Document {text_document!r} not found.",
                )

            self.create_document_diagnostics_task(document, True)

            return RelatedFullDocumentDiagnosticReport([])
        except CancelledError:
            self._logger.debug("canceled _text_document_diagnostic")
            raise

    def get_diagnostics_data(self, document: TextDocument) -> DiagnosticsData:
        data: DiagnosticsData = document.get_data(self, None)

        if data is None:
            data = DiagnosticsData(str(uuid.uuid4()))  # type: ignore
            document.set_data(self, data)

        return data

    @rpc_method(name="workspace/diagnostic", param_type=WorkspaceDiagnosticParams, threaded=True)
    def _workspace_diagnostic(
        self,
        identifier: Optional[str],
        previous_result_ids: List[PreviousResultId],
        partial_result_token: Optional[ProgressToken],
        work_done_token: Optional[ProgressToken] = None,
        *args: Any,
        **kwargs: Any,
    ) -> WorkspaceDiagnosticReport:
        self._logger.debug("workspace/diagnostic")

        return WorkspaceDiagnosticReport(items=[])

    def get_analysis_progress_mode(self, uri: Uri) -> AnalysisProgressMode:
        for e in self.on_get_analysis_progress_mode(self, uri):
            if e is not None:
                return cast(AnalysisProgressMode, e)

        return AnalysisProgressMode.OFF

    def get_diagnostics_mode(self, uri: Uri) -> DiagnosticsMode:
        for e in self.on_get_diagnostics_mode(self, uri):
            if e is not None:
                return cast(DiagnosticsMode, e)

        return DiagnosticsMode.OPENFILESONLY

    def refresh(self, now: bool = False) -> None:
        if self.refresh_task is not None and not self.refresh_task.done():
            self.refresh_task.cancel()

        self.refresh_task = run_in_thread(self._refresh, now)

    def _refresh(self, now: bool = False) -> None:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.diagnostics
            and self.parent.client_capabilities.workspace.diagnostics.refresh_support
        ):
            if not now:
                check_current_thread_canceled(1)

            self.parent.send_request("workspace/diagnostic/refresh").result(self._refresh_timeout)
