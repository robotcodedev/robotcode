import concurrent.futures
import functools
import itertools
import logging
import time
import uuid
from concurrent.futures import CancelledError
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from threading import Event, Timer
from typing import TYPE_CHECKING, Any, Dict, Final, Iterator, List, Optional, Union, cast

from robotcode.core.concurrent import Lock, RLock, Task, check_current_task_canceled, run_as_task
from robotcode.core.event import event
from robotcode.core.language import language_id_filter
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
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import JsonRPCErrorException, rpc_method
from robotcode.language_server.common.parts.protocol_part import (
    LanguageServerProtocolPart,
)

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
    skipped: bool = False


@dataclass
class DiagnosticsData:
    lock: RLock
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entries: Dict[Any, Optional[List[Diagnostic]]] = field(default_factory=dict)
    version: Optional[int] = None
    future: Optional[Task[Any]] = None
    force: bool = False
    single: bool = False
    skipped_entries: bool = False


class DiagnosticsCollectType(Enum):
    NORMAL = 0
    SLOW = 1


class DiagnosticsProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, protocol: "LanguageServerProtocol") -> None:
        super().__init__(protocol)

        self.workspace_loaded_event = Event()

        self._workspace_load_lock = Lock()
        self._workspace_loaded = False

        self._workspace_diagnostics_task: Optional[Task[Any]] = None

        self.parent.on_initialized.add(self.server_initialized)

        self.parent.on_exit.add(self.cancel_workspace_diagnostics_task)
        self.parent.on_shutdown.add(self.cancel_workspace_diagnostics_task)

        self.parent.documents.on_document_cache_invalidated.add(self._on_document_cache_invalidated)
        self.parent.documents.did_close.add(self.on_did_close)

        self.in_get_workspace_diagnostics_event = Event()
        self.workspace_diagnostics_started_event = Event()

        self.client_supports_pull = False

        self.refresh_timer_lock = RLock()
        self.refresh_timer: Optional[Timer] = None

        self.break_diagnostics_timer_lock = RLock()
        self.break_diagnostics_timer: Optional[Timer] = None
        self._break_diagnostics_loop_event = Event()

        self._current_diagnostics_task_lock = RLock()
        self._current_diagnostics_task: Optional[Task[Any]] = None
        self._diagnostics_task_timeout = 300

    def server_initialized(self, sender: Any) -> None:
        if not self.client_supports_pull:
            self.parent.documents.did_open.add(self.update_document_diagnostics)
            self.parent.documents.did_change.add(self.update_document_diagnostics)
            self.parent.documents.did_save.add(self.update_document_diagnostics)

        self._workspace_diagnostics_task = run_as_task(self.run_workspace_diagnostics)

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
    def analyze(sender, document: TextDocument) -> Optional[DiagnosticsResult]: ...

    @event
    def collect(
        sender, document: TextDocument, diagnostics_type: DiagnosticsCollectType
    ) -> Optional[DiagnosticsResult]: ...

    @event
    def load_workspace_documents(
        sender,
    ) -> None: ...

    @event
    def on_workspace_loaded(sender: Any) -> None: ...

    @event
    def on_get_related_documents(sender: Any, document: TextDocument) -> Optional[List[TextDocument]]: ...

    @event
    def on_get_analysis_progress_mode(sender: Any, uri: Uri) -> Optional[AnalysisProgressMode]: ...

    @event
    def on_get_diagnostics_mode(sender: Any, uri: Uri) -> Optional[DiagnosticsMode]: ...

    @event
    def on_workspace_diagnostics_start(sender: Any) -> None: ...

    @event
    def on_workspace_diagnostics_analyze(sender: Any) -> None: ...

    @event
    def on_workspace_diagnostics_collect(sender: Any) -> None: ...

    @event
    def on_workspace_diagnostics_end(sender: Any) -> None: ...

    @event
    def on_workspace_diagnostics_break(sender: Any) -> None: ...

    def ensure_workspace_loaded(self) -> None:
        self.parent.ensure_initialized()

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

    def get_related_documents(
        self, document: TextDocument, result: Optional[List[TextDocument]] = None
    ) -> List[TextDocument]:
        start = time.monotonic()
        self._logger.debug(lambda: f"start get_related_documents for {document}")
        try:
            return self._get_related_documents(document)
        finally:
            self._logger.debug(lambda: f"end get_related_documents for {document} takes {time.monotonic() - start}s")

    def _get_related_documents(
        self, document: TextDocument, result: Optional[List[TextDocument]] = None
    ) -> List[TextDocument]:
        if result is None:
            result = []

        for docs in self.on_get_related_documents(self, document):
            check_current_task_canceled()

            if docs is not None:

                if isinstance(docs, BaseException):
                    if not isinstance(docs, CancelledError):
                        self._logger.exception(docs, exc_info=result)
                    continue

                for doc in docs:
                    if doc not in result and doc is not document:
                        result.append(doc)
                        self._get_related_documents(doc, result)

        return result

    def __on_document_cache_invalidated(self, document: TextDocument) -> None:
        start = time.monotonic()
        self._logger.debug(lambda: f"start on_document_cache_invalidated for {document}")
        try:
            needs_refresh = False
            needs_break = False
            for doc in (document, *self.get_related_documents(document)):
                needs_refresh = needs_refresh or doc.opened_in_editor
                needs_break = needs_break or doc.opened_in_editor
                doc.set_data(DiagnosticsProtocolPart, None)
                with self.get_diagnostics_data(doc) as data:
                    if data.force:
                        continue
                    needs_break = True
                    data.force = True

            if needs_break:
                self.break_workspace_diagnostics_loop()

            if needs_refresh:
                self.refresh()
        except BaseException as e:
            self._logger.exception(e)
        finally:
            self._logger.debug(
                lambda: f"end on_document_cache_invalidated for {document} takes {time.monotonic() - start}s"
            )

    def _on_document_cache_invalidated(self, sender: Any, document: TextDocument) -> None:
        run_as_task(self.__on_document_cache_invalidated, document)

    def force_refresh_all(self, refresh: bool = True) -> None:
        for doc in self.parent.documents.documents:
            with self.get_diagnostics_data(doc) as data:
                data.force = True

        if refresh:
            self.refresh()

    def force_refresh_document(self, document: TextDocument, refresh: bool = True, single: bool = False) -> None:
        with self.get_diagnostics_data(document) as data:
            if data.force:
                return
            data.force = True
            data.single = single
        if refresh and document.opened_in_editor:
            self.refresh()

    @_logger.call
    def on_did_close(self, sender: Any, document: TextDocument, full_close: bool) -> None:
        run_as_task(self._close_diagnostics_for_document, document, full_close)

    def _close_diagnostics_for_document(self, document: TextDocument, full_close: bool) -> None:
        if not full_close and self.get_diagnostics_mode(document.uri) == DiagnosticsMode.WORKSPACE:
            return

        try:
            with self.get_diagnostics_data(document) as data:
                if data.future is not None and not data.future.done():
                    self._logger.debug(lambda: f"try to cancel diagnostics for {document}")

                    data.future.cancel()
        finally:
            self.publish_diagnostics(document, diagnostics=[])

    def cancel_workspace_diagnostics_task(self, sender: Any) -> None:
        if self._current_diagnostics_task is not None and not self._current_diagnostics_task.done():
            self._current_diagnostics_task.cancel()

        if self._workspace_diagnostics_task is not None and not self._workspace_diagnostics_task.done():
            self._workspace_diagnostics_task.cancel()

    def break_workspace_diagnostics_loop(self, now: bool = False) -> None:
        with self.break_diagnostics_timer_lock:
            if self.break_diagnostics_timer is not None:
                self.break_diagnostics_timer.cancel()
                self.break_diagnostics_timer = None

            if not now:
                self.break_diagnostics_timer = Timer(1, self._break_workspace_diagnostics_loop)
                self.break_diagnostics_timer.start()
                return

        self._break_workspace_diagnostics_loop()

    def _break_workspace_diagnostics_loop(self) -> None:
        self._break_diagnostics_loop_event.set()
        with self._current_diagnostics_task_lock(timeout=self._diagnostics_task_timeout * 2):
            if self._current_diagnostics_task is not None and not self._current_diagnostics_task.done():
                self._current_diagnostics_task.cancel()

    def _analyse_document(self, document: TextDocument) -> List[Union[DiagnosticsResult, None, BaseException]]:
        return self.analyze(
            self,
            document,
            callback_filter=language_id_filter(document),
            return_exceptions=True,
        )

    def _doc_need_update(self, document: TextDocument) -> bool:
        with self.get_diagnostics_data(document) as data:
            return data.force or document.version != data.version or data.skipped_entries

    @_logger.call
    def run_workspace_diagnostics(self) -> None:
        self._logger.debug("start workspace diagnostics loop")
        self.ensure_workspace_loaded()

        while True:

            check_current_task_canceled()

            self.on_workspace_diagnostics_start(self)
            self.in_get_workspace_diagnostics_event.clear()
            self.workspace_diagnostics_started_event.set()
            done_something = False

            try:
                self._break_diagnostics_loop_event.clear()

                documents = sorted(
                    [doc for doc in self.parent.documents.documents if self._doc_need_update(doc)],
                    key=lambda d: not d.opened_in_editor,
                )

                if len(documents) == 0:
                    check_current_task_canceled(1)
                    continue

                with self._logger.measure_time(
                    lambda: f"analyzing workspace for {len(documents)} documents",
                    context_name="workspace_diagnostics",
                    level=logging.CRITICAL,
                ):

                    self.on_workspace_diagnostics_analyze(self)

                    if self._break_diagnostics_loop_event.is_set():
                        self._logger.debug("break workspace diagnostics loop 1", context_name="workspace_diagnostics")
                        self.on_workspace_diagnostics_break(self)
                        continue

                    with self.parent.window.progress(
                        "Analyze Workspace",
                        cancellable=False,
                        current=0,
                        max=len(documents),
                        start=False,
                    ) as progress:
                        breaked = False
                        for i, document in enumerate(documents):
                            check_current_task_canceled()

                            if breaked or self._break_diagnostics_loop_event.is_set():
                                self._logger.debug(
                                    "break workspace diagnostics loop 2", context_name="workspace_diagnostics"
                                )
                                breaked = True
                                self.on_workspace_diagnostics_break(self)
                                break

                            done_something = True

                            analysis_mode = self.get_analysis_progress_mode(document.uri)

                            if analysis_mode == AnalysisProgressMode.DETAILED:
                                progress.begin()
                                path = document.uri.to_path()
                                folder = self.parent.workspace.get_workspace_folder(document.uri)
                                name = path if folder is None else path.relative_to(folder.uri.to_path())

                                progress.report(f"Analyze {i+1}/{len(documents)}: {name}", current=i + 1)
                            elif analysis_mode == AnalysisProgressMode.SIMPLE:
                                progress.begin()
                                progress.report(f"Analyze {i+1}/{len(documents)}", current=i + 1)

                            try:
                                with self._current_diagnostics_task_lock:
                                    self._current_diagnostics_task = run_as_task(self._analyse_document, document)
                                self._current_diagnostics_task.result(self._diagnostics_task_timeout)

                            except CancelledError:
                                self._logger.debug(
                                    lambda: f"Analyzing {document.uri} cancelled", context_name="workspace_diagnostics"
                                )
                                breaked = True
                            except BaseException as e:
                                ex = e
                                self._logger.exception(
                                    lambda: f"Error in analyzing ${document.uri}: {ex}",
                                    exc_info=ex,
                                    context_name="workspace_diagnostics",
                                )
                            finally:
                                with self._current_diagnostics_task_lock:
                                    self._current_diagnostics_task = None

                    if breaked or self._break_diagnostics_loop_event.is_set():
                        self._logger.debug("break workspace diagnostics loop 3", context_name="workspace_diagnostics")
                        self.on_workspace_diagnostics_break(self)
                        continue

                self.on_workspace_diagnostics_collect(self)

                documents_to_collect = [
                    doc
                    for doc in documents
                    if doc.opened_in_editor or self.get_diagnostics_mode(document.uri) == DiagnosticsMode.WORKSPACE
                ]

                with self._logger.measure_time(
                    lambda: f"collect workspace diagnostic for {len(documents_to_collect)} documents",
                    context_name="collect_workspace_diagnostics",
                    level=logging.CRITICAL,
                ):
                    breaked = False
                    for document in set(documents) - set(documents_to_collect):
                        check_current_task_canceled()

                        if breaked or self._break_diagnostics_loop_event.is_set():
                            self._logger.debug("break workspace diagnostics loop 4")
                            breaked = True
                            self.on_workspace_diagnostics_break(self)
                            break

                        self.reset_document_diagnostics_data(document)

                    with self.parent.window.progress(
                        "Collect Diagnostics",
                        cancellable=False,
                        current=0,
                        max=len(documents_to_collect),
                        start=False,
                    ) as progress:
                        for i, document in enumerate(documents_to_collect):
                            check_current_task_canceled()

                            if self._break_diagnostics_loop_event.is_set():
                                self._logger.debug(
                                    "break workspace diagnostics loop 5", context_name="collect_workspace_diagnostics"
                                )
                                self.on_workspace_diagnostics_break(self)
                                break

                            mode = self.get_diagnostics_mode(document.uri)
                            if mode == DiagnosticsMode.OFF:
                                self.reset_document_diagnostics_data(document)
                                continue

                            done_something = True

                            analysis_mode = self.get_analysis_progress_mode(document.uri)

                            if analysis_mode == AnalysisProgressMode.DETAILED:
                                progress.begin()
                                path = document.uri.to_path()
                                folder = self.parent.workspace.get_workspace_folder(document.uri)
                                name = path if folder is None else path.relative_to(folder.uri.to_path())

                                progress.report(f"Collect {i+1}/{len(documents_to_collect)}: {name}", current=i + 1)
                            elif analysis_mode == AnalysisProgressMode.SIMPLE:
                                progress.begin()
                                progress.report(f"Collect {i+1}/{len(documents_to_collect)}", current=i + 1)

                            try:
                                with self._current_diagnostics_task_lock:
                                    self._current_diagnostics_task = self.create_document_diagnostics_task(
                                        document,
                                        False,
                                        mode == DiagnosticsMode.WORKSPACE or document.opened_in_editor,
                                    )
                                if self._current_diagnostics_task is not None:
                                    self._current_diagnostics_task.result(self._diagnostics_task_timeout)
                            except CancelledError:
                                self._logger.debug(
                                    lambda: f"Collecting diagnostics for {document.uri} cancelled",
                                    context_name="collect_workspace_diagnostics",
                                )
                                breaked = True
                            except BaseException as e:
                                ex = e
                                self._logger.exception(
                                    lambda: f"Error getting diagnostics for ${document.uri}: {ex}",
                                    exc_info=ex,
                                    context_name="collect_workspace_diagnostics",
                                )
                            finally:
                                with self._current_diagnostics_task_lock:
                                    self._current_diagnostics_task = None

            except (SystemExit, KeyboardInterrupt, CancelledError):
                raise
            except BaseException as e:
                self._logger.exception(e)
            finally:
                self.workspace_diagnostics_started_event.clear()
                self.in_get_workspace_diagnostics_event.set()
                self.on_workspace_diagnostics_end(self)

                if not done_something:
                    check_current_task_canceled(1)

    def reset_document_diagnostics_data(self, document: TextDocument) -> None:
        with self.get_diagnostics_data(document) as data:
            data.force = False
            data.version = document.version
            data.skipped_entries = False
            data.single = False

    def _diagnostics_task_done(self, document: TextDocument, data: DiagnosticsData, task: Task[Any]) -> None:
        if task.done() and not task.cancelled():
            with data.lock:
                data.single = False

    def create_document_diagnostics_task(
        self,
        document: TextDocument,
        debounce: bool = True,
        send_diagnostics: bool = True,
    ) -> Task[Any]:

        with self.get_diagnostics_data(document) as data:

            if data.force or document.version != data.version or data.future is None or data.skipped_entries:
                future = data.future
                collect_slow = not data.single
                if data.single:
                    data.single = False
                else:
                    data.force = False

                if future is not None and not future.done():
                    self._logger.debug(lambda: f"try to cancel diagnostics for {document}")

                    future.cancel()
                    try:
                        concurrent.futures.wait([future], timeout=5)
                    except BaseException as e:
                        self._logger.exception(e)

                data.version = document.version
                data.future = run_as_task(
                    self._get_diagnostics_for_document, document, data, debounce, send_diagnostics, collect_slow
                )

                data.future.add_done_callback(functools.partial(self._diagnostics_task_done, document, data))
            else:
                self._logger.debug(lambda: f"skip diagnostics for {document}")

            return data.future

    @_logger.call
    def _get_diagnostics_for_document(
        self,
        document: TextDocument,
        data: DiagnosticsData,
        debounce: bool,
        send_diagnostics: bool,
        collect_slow: bool,
    ) -> None:
        if debounce:
            check_current_task_canceled(0.75)

        data.skipped_entries = False
        collected_keys: List[Any] = []
        try:
            for result in self.collect(
                self,
                document,
                DiagnosticsCollectType.SLOW if collect_slow else DiagnosticsCollectType.NORMAL,
                callback_filter=language_id_filter(document),
                return_exceptions=True,
            ):
                check_current_task_canceled()

                if isinstance(result, BaseException):
                    if not isinstance(result, CancelledError):
                        self._logger.exception(result, exc_info=result)
                    continue
                if result is None:
                    continue

                data.id = str(uuid.uuid4())
                if result.skipped:
                    data.skipped_entries = True

                if result.diagnostics is not None:
                    for d in result.diagnostics:
                        d.range = document.range_to_utf16(d.range)

                        for r in d.related_information or []:
                            doc = self.parent.documents.get(r.location.uri)
                            if doc is not None:
                                r.location.range = doc.range_to_utf16(r.location.range)

                if not result.skipped:
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
        self.force_refresh_document(document, refresh=True)

    @rpc_method(name="textDocument/diagnostic", param_type=DocumentDiagnosticParams, threaded=True)
    def _text_document_diagnostic(
        self,
        text_document: TextDocumentIdentifier,
        identifier: Optional[str],
        previous_result_id: Optional[str],
        *args: Any,
        **kwargs: Any,
    ) -> DocumentDiagnosticReport:
        self.parent.ensure_initialized()

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

            self.force_refresh_document(document, refresh=False, single=True)
            self.break_workspace_diagnostics_loop()

            # task = self.create_document_diagnostics_task(document, True, collect_slow=False)
            # if task is not None:
            #     task.result(self._diagnostics_task_timeout)

            return RelatedFullDocumentDiagnosticReport([])
        except CancelledError:
            self._logger.debug("canceled _text_document_diagnostic")
            raise

    @contextmanager
    def get_diagnostics_data(self, document: TextDocument) -> Iterator[DiagnosticsData]:
        data: Optional[DiagnosticsData] = document.get_data(DiagnosticsProtocolPart, None)

        if data is None:
            data = DiagnosticsData(
                RLock(default_timeout=self._diagnostics_task_timeout, name=f"diagnostics data for {document}"),
                str(uuid.uuid4()),
            )
            document.set_data(DiagnosticsProtocolPart, data)

        with data.lock:
            yield data

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
        with self.refresh_timer_lock:
            if self.refresh_timer is not None:
                self.refresh_timer.cancel()
                self.refresh_timer = None

            if not now:
                self.refresh_timer = Timer(1, self._refresh)
                self.refresh_timer.start()
                return

        self._refresh()

    def _refresh(self) -> None:
        with self.refresh_timer_lock:
            self.refresh_timer = None

        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.diagnostics
            and self.parent.client_capabilities.workspace.diagnostics.refresh_support
        ):
            self.parent.send_request("workspace/diagnostic/refresh")
