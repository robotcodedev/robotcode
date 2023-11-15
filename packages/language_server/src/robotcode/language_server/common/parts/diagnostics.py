from __future__ import annotations

import asyncio
import itertools
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Final, List, Optional, cast

from robotcode.core.async_tools import (
    Event,
    Lock,
    async_event,
    async_tasking_event,
    async_tasking_event_iterator,
    check_canceled,
    create_sub_task,
    threaded,
)
from robotcode.core.logging import LoggingDescriptor
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
from robotcode.jsonrpc2.protocol import JsonRPCErrorException, rpc_method
from robotcode.language_server.common.decorators import language_id_filter
from robotcode.language_server.common.has_extend_capabilities import HasExtendCapabilities
from robotcode.language_server.common.parts.protocol_part import LanguageServerProtocolPart
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
    task: Optional[asyncio.Task[Any]] = None
    force: bool = False


def _cancel_all_tasks(loop: asyncio.AbstractEventLoop) -> None:
    to_cancel = asyncio.all_tasks(loop)
    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler(
                {
                    "message": "unhandled exception during asyncio.run() shutdown",
                    "exception": task.exception(),
                    "task": task,
                }
            )


class DiagnosticsProtocolPart(LanguageServerProtocolPart, HasExtendCapabilities):
    _logger: Final = LoggingDescriptor()

    def __init__(self, protocol: LanguageServerProtocol) -> None:
        super().__init__(protocol)

        self.workspace_loaded_event = Event()

        self._workspace_load_lock = Lock()
        self._workspace_loaded = False

        self._workspace_diagnostics_task: Optional[asyncio.Task[Any]] = None

        self._diagnostics_loop: Optional[asyncio.AbstractEventLoop] = None
        self._single_diagnostics_loop: Optional[asyncio.AbstractEventLoop] = None

        self._diagnostics_loop_lock = threading.RLock()
        self._diagnostics_started = threading.Event()
        self._single_diagnostics_started = threading.Event()

        self._diagnostics_server_thread: Optional[threading.Thread] = None
        self._single_diagnostics_server_thread: Optional[threading.Thread] = None

        self.parent.on_initialized.add(self.initialized)

        self.parent.on_exit.add(self.cancel_workspace_diagnostics_task)

        self.parent.documents.did_close.add(self.on_did_close)

        self.in_get_workspace_diagnostics = Event(True)

        self.refresh_task: Optional[asyncio.Task[Any]] = None

        self.client_supports_pull = False

    async def initialized(self, sender: Any) -> None:
        self._ensure_diagnostics_thread_started()

        self._workspace_diagnostics_task = create_sub_task(self.run_workspace_diagnostics(), loop=self.diagnostics_loop)

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

    @property
    def diagnostics_loop(self) -> asyncio.AbstractEventLoop:
        if self._diagnostics_loop is None:
            self._ensure_diagnostics_thread_started()

        assert self._diagnostics_loop is not None

        return self._diagnostics_loop

    @property
    def single_diagnostics_loop(self) -> asyncio.AbstractEventLoop:
        if self._single_diagnostics_loop is None:
            self._ensure_diagnostics_thread_started()

        assert self._single_diagnostics_loop is not None

        return self._single_diagnostics_loop

    def _run_diagnostics(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self._diagnostics_loop = loop
            self._diagnostics_started.set()

            loop.slow_callback_duration = 10

            loop.run_forever()
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    def _single_run_diagnostics(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self._single_diagnostics_loop = loop
            self._single_diagnostics_started.set()

            loop.slow_callback_duration = 10

            loop.run_forever()
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    def _ensure_diagnostics_thread_started(self) -> None:
        with self._diagnostics_loop_lock:
            if self._diagnostics_loop is None:
                self._diagnostics_server_thread = threading.Thread(
                    name="diagnostics_worker", target=self._run_diagnostics, daemon=True
                )

                self._diagnostics_server_thread.start()

                self._single_diagnostics_server_thread = threading.Thread(
                    name="single_diagnostics_worker", target=self._single_run_diagnostics, daemon=True
                )

                self._single_diagnostics_server_thread.start()

                if not self._diagnostics_started.wait(10) or not self._single_diagnostics_started.wait(10):
                    raise RuntimeError("Can't start diagnostics worker threads.")

    @async_tasking_event_iterator
    async def collect(sender, document: TextDocument) -> Optional[DiagnosticsResult]:  # NOSONAR
        ...

    @async_tasking_event
    async def load_workspace_documents(sender) -> Optional[List[WorkspaceDocumentsResult]]:  # NOSONAR
        ...

    @async_tasking_event
    async def on_workspace_loaded(sender) -> None:  # NOSONAR
        ...

    @async_event
    async def on_get_analysis_progress_mode(sender, uri: Uri) -> Optional[AnalysisProgressMode]:  # NOSONAR
        ...

    @async_event
    async def on_get_diagnostics_mode(sender, uri: Uri) -> Optional[DiagnosticsMode]:  # NOSONAR
        ...

    async def ensure_workspace_loaded(self) -> None:
        async with self._workspace_load_lock:
            if not self._workspace_loaded and not self.workspace_loaded_event.is_set():
                self._logger.debug("load workspace documents")
                try:
                    await self.load_workspace_documents(self)
                finally:
                    self._workspace_loaded = True
                    self.workspace_loaded_event.set()
                    await self.on_workspace_loaded(self)
                    await self.force_refresh_all()

    async def force_refresh_all(self, refresh: bool = True) -> None:
        for doc in self.parent.documents.documents:
            self.get_diagnostics_data(doc).force = True

        if refresh:
            await self.refresh()

    async def force_refresh_document(self, document: TextDocument, refresh: bool = True) -> None:
        self.get_diagnostics_data(document).force = True
        if refresh and document.opened_in_editor:
            await self.refresh()

    @_logger.call
    @threaded()
    async def on_did_close(self, sender: Any, document: TextDocument) -> None:
        if await self.get_diagnostics_mode(document.uri) == DiagnosticsMode.WORKSPACE:
            return

        try:
            data = self.get_diagnostics_data(document)
            if data.task is not None and not data.task.done():
                self._logger.debug(lambda: f"try to cancel diagnostics for {document}")

                e = threading.Event()

                def done(t: asyncio.Task[Any]) -> None:
                    e.set()

                data.task.add_done_callback(done)
                data.task.get_loop().call_soon_threadsafe(data.task.cancel)

                start = time.monotonic()
                while not e.is_set():
                    if time.monotonic() - start > 120:
                        break

                    await asyncio.sleep(0.001)

        finally:
            self.publish_diagnostics(document, diagnostics=[])

    async def cancel_workspace_diagnostics_task(self, sender: Any) -> None:
        if self._workspace_diagnostics_task is not None:
            self._workspace_diagnostics_task.get_loop().call_soon_threadsafe(self._workspace_diagnostics_task.cancel)

    @_logger.call
    async def run_workspace_diagnostics(self) -> None:
        self._logger.debug("start workspace diagnostics loop")
        await self.ensure_workspace_loaded()

        while True:
            try:
                documents = [
                    doc
                    for doc in self.parent.documents.documents
                    if not doc.opened_in_editor
                    and (
                        (data := self.get_diagnostics_data(doc)).force
                        or doc.version != data.version
                        or data.task is None
                    )
                ]

                if len(documents) == 0:
                    await asyncio.sleep(1)
                    continue

                self._logger.info(lambda: f"start collecting workspace diagnostics for {len(documents)} documents")

                done_something = False

                start = time.monotonic()
                async with self.parent.window.progress(
                    "Analyse workspace", cancellable=False, current=0, max=len(documents) + 1, start=False
                ) as progress:
                    for i, document in enumerate(documents):
                        mode = await self.get_diagnostics_mode(document.uri)
                        if mode == DiagnosticsMode.OFF:
                            self.get_diagnostics_data(document).version = document.version
                            continue

                        if document.opened_in_editor:
                            continue

                        done_something = True

                        analysis_mode = await self.get_analysis_progress_mode(document.uri)

                        if analysis_mode == AnalysisProgressMode.DETAILED:
                            progress.begin()
                            path = document.uri.to_path()
                            folder = self.parent.workspace.get_workspace_folder(document.uri)
                            name = path if folder is None else path.relative_to(folder.uri.to_path())

                            progress.report(f"Analyse {name}", current=i + 1)
                        elif analysis_mode == AnalysisProgressMode.SIMPLE:
                            progress.begin()
                            progress.report(current=i + 1)

                        await self.create_document_diagnostics_task(
                            document,
                            False,
                            False,
                            mode == DiagnosticsMode.WORKSPACE,
                        )

                if not done_something:
                    await asyncio.sleep(1)

                self._logger.info(
                    lambda: f"collecting workspace diagnostics for {len(documents)} "
                    f"documents takes {time.monotonic() - start}s"
                )

            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                raise
            except BaseException as e:
                ex = e
                self._logger.exception(lambda: f"Error in workspace diagnostics loop: {ex}", exc_info=e)

    def create_document_diagnostics_task(
        self, document: TextDocument, single: bool, debounce: bool = True, send_diagnostics: bool = True
    ) -> asyncio.Task[Any]:
        def done(t: asyncio.Task[Any]) -> None:
            self._logger.debug(lambda: f"diagnostics for {document} {'canceled' if t.cancelled() else 'ended'}")

            if t.done() and not t.cancelled():
                ex = t.exception()

                if ex is None or isinstance(ex, asyncio.CancelledError):
                    return

        data = self.get_diagnostics_data(document)

        if data.force or document.version != data.version or data.task is None:
            task = data.task

            data.force = False

            if task is not None and not task.done():
                self._logger.debug(lambda: f"try to cancel diagnostics for {document}")

                async def cancel(t: asyncio.Task[Any]) -> None:
                    t.cancel()
                    try:
                        await t
                    except asyncio.CancelledError:
                        pass

                try:
                    asyncio.run_coroutine_threadsafe(cancel(task), loop=task.get_loop()).result(600)
                except TimeoutError as e:
                    raise RuntimeError("Can't cancel diagnostics task.") from e

            data.version = document.version
            data.task = create_sub_task(
                self._get_diagnostics_for_document(document, data, debounce, send_diagnostics),
                loop=self.single_diagnostics_loop if single else self.diagnostics_loop,
                name=f"diagnostics ${document.uri}",
            )

            data.task.add_done_callback(done)

        return data.task

    @_logger.call
    async def _get_diagnostics_for_document(
        self, document: TextDocument, data: DiagnosticsData, debounce: bool = True, send_diagnostics: bool = True
    ) -> None:
        self._logger.debug(lambda: f"Get diagnostics for {document}")

        if debounce:
            await asyncio.sleep(0.75)

        collected_keys: List[Any] = []
        try:
            async for result_any in self.collect(
                self, document, callback_filter=language_id_filter(document), return_exceptions=True
            ):
                await check_canceled()

                if isinstance(result_any, BaseException):
                    if not isinstance(result_any, asyncio.CancelledError):
                        self._logger.exception(result_any, exc_info=result_any)
                    continue
                if result_any is None:
                    continue

                result = cast(DiagnosticsResult, result_any)

                data.id = str(uuid.uuid4())

                if result.diagnostics is not None:
                    for d in result.diagnostics:
                        d.range = document.range_to_utf16(d.range)

                        for r in d.related_information or []:
                            doc = await self.parent.documents.get(r.location.uri)
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

        except asyncio.CancelledError:
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

    async def update_document_diagnostics(self, sender: Any, document: TextDocument) -> None:
        self.create_document_diagnostics_task(document, True)

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
        try:
            if not self.parent.is_initialized:
                raise JsonRPCErrorException(
                    LSPErrorCodes.SERVER_CANCELLED, "Server not initialized.", DiagnosticServerCancellationData(True)
                )

            document = await self.parent.documents.get(text_document.uri)
            if document is None:
                raise JsonRPCErrorException(LSPErrorCodes.SERVER_CANCELLED, f"Document {text_document!r} not found.")

            self.create_document_diagnostics_task(document, True)

            return RelatedFullDocumentDiagnosticReport([])
        except asyncio.CancelledError:
            self._logger.debug("canceled _text_document_diagnostic")
            raise

    def get_diagnostics_data(self, document: TextDocument) -> DiagnosticsData:
        data: DiagnosticsData = document.get_data(self, None)

        if data is None:
            data = DiagnosticsData(str(uuid.uuid4()))  # type: ignore
            document.set_data(self, data)

        return data

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

        return WorkspaceDiagnosticReport(items=[])

    async def get_analysis_progress_mode(self, uri: Uri) -> AnalysisProgressMode:
        for e in await self.on_get_analysis_progress_mode(self, uri):
            if e is not None:
                return cast(AnalysisProgressMode, e)

        return AnalysisProgressMode.OFF

    async def get_diagnostics_mode(self, uri: Uri) -> DiagnosticsMode:
        for e in await self.on_get_diagnostics_mode(self, uri):
            if e is not None:
                return cast(DiagnosticsMode, e)

        return DiagnosticsMode.OPENFILESONLY

    async def __do_refresh(self, now: bool = False) -> None:
        if not now:
            await asyncio.sleep(1)

        await self.__refresh()

    async def refresh(self, now: bool = False) -> None:
        if self.refresh_task is not None and not self.refresh_task.done():
            self.refresh_task.get_loop().call_soon_threadsafe(self.refresh_task.cancel)

        self.refresh_task = create_sub_task(self.__do_refresh(now), loop=self.diagnostics_loop)

    async def __refresh(self) -> None:
        if (
            self.parent.client_capabilities
            and self.parent.client_capabilities.workspace
            and self.parent.client_capabilities.workspace.diagnostics
            and self.parent.client_capabilities.workspace.diagnostics.refresh_support
        ):
            await self.parent.send_request_async("workspace/diagnostic/refresh")
