import asyncio
from typing import Generic, List, TYPE_CHECKING, Any, Callable, Dict, Optional, cast

from ...utils.async_event import AsyncThreadingEvent
from ...utils.logging import LoggingDescriptor
from ...jsonrpc2.protocol import JsonRPCProtocol
from ..text_document import TextDocument
from .documents import TDocument
from ..types import Diagnostic, DocumentUri, PublishDiagnosticsParams

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart

__all__ = ["DiagnosticsProtocolPart"]

DIAGNOSTICS_DEBOUNCE = 0.75


class PublishDiagnosticsEntry:
    _logger = LoggingDescriptor()

    def __init__(self, document: TextDocument, task_factory: Callable[..., asyncio.Task[Any]]) -> None:

        self._document = document
        self._task_factory = task_factory

        self._task: Optional[asyncio.Task[Any]] = None

        @PublishDiagnosticsEntry._logger.call
        def create_task() -> None:
            self._task = self._task_factory()

            if self._task is not None:
                self._task.set_name(f"Diagnostics for {document}")

                def _done(t: asyncio.Task[Any]) -> None:
                    self._task = None

                self._task.add_done_callback(_done)

        self._timer_handle: asyncio.TimerHandle = asyncio.get_event_loop().call_later(DIAGNOSTICS_DEBOUNCE, create_task)

    def __del__(self) -> None:
        self.cancel(_from_del=True)

    @property
    def document(self) -> TextDocument:
        return self._document

    @property
    def task(self) -> Optional[asyncio.Task[Any]]:
        return self._task

    def __str__(self) -> str:
        return f"{type(self)}(document={repr(self.document)}, task={repr(self.task)})"

    def __repr__(self) -> str:
        return f"{type(self)}(document={repr(self.document)}, task={repr(self.task)})"

    @_logger.call(condition=lambda self, _from_del=False: not _from_del)
    def cancel(self, *, _from_del: Optional[bool] = False) -> None:
        self._timer_handle.cancel()

        if self.task is None:
            return

        async def cancel() -> None:
            if self.task is None:
                return

            t = self.task
            self._task = None
            if not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
                except BaseException:
                    pass

        asyncio.ensure_future(cancel())


class DiagnosticsProtocolPart(LanguageServerProtocolPart, Generic[TDocument]):
    _logger = LoggingDescriptor()

    def __init__(self, protocol: "LanguageServerProtocol") -> None:
        super().__init__(protocol)

        self._running_diagnosistcs: Dict[DocumentUri, PublishDiagnosticsEntry] = {}
        self._task_lock = asyncio.Lock()
        self._start_lock_lock = asyncio.Lock()

        self.collect_diagnostics_event = AsyncThreadingEvent[
            DiagnosticsProtocolPart[TDocument], TDocument, List[Diagnostic]
        ]()

        self.parent.connection_lost_event.add(self.on_connection_lost)
        self.parent.shutdown_event.add(self.on_shutdown)
        self.parent.documents.did_open_event.add(self.on_did_open)
        self.parent.documents.did_change_event.add(self.on_did_change)
        self.parent.documents.did_close_event.add(self.on_did_close)
        self.parent.documents.did_save_event.add(self.on_did_save)

    @_logger.call
    async def on_connection_lost(self, sender: JsonRPCProtocol, ex: BaseException) -> None:
        await self._cancel_all_tasks()

    @_logger.call
    async def on_shutdown(self, sender: "LanguageServerProtocol", param: Any) -> None:
        await self._cancel_all_tasks()

    def __del__(self) -> None:
        if len(self._running_diagnosistcs) > 0:
            self._logger.warning("there are running tasks")

    @_logger.call
    async def _cancel_all_tasks(self) -> None:
        tasks_copy = None
        async with self._task_lock:
            tasks_copy = self._running_diagnosistcs.copy()
            self._running_diagnosistcs = {}
        if tasks_copy is not None:
            for v in tasks_copy.values():
                self._cancel_entry(v)

    @_logger.call(condition=lambda self, entry: entry is not None)
    def _cancel_entry(self, entry: Optional[PublishDiagnosticsEntry]) -> None:
        if entry is None:
            return

        entry.cancel()

    @_logger.call
    async def on_did_open(self, sender: Any, document: TextDocument) -> None:
        await self.start_publish_diagnostics_task(cast("TDocument", document))

    @_logger.call
    async def on_did_save(self, sender: Any, document: TextDocument) -> None:
        await self.start_publish_diagnostics_task(cast("TDocument", document))

    @_logger.call
    async def on_did_close(self, sender: Any, document: TextDocument) -> None:
        async with self._task_lock:
            e = self._running_diagnosistcs.pop(document.uri, None)
            self._cancel_entry(e)

    @_logger.call
    async def on_did_change(self, sender: Any, document: TextDocument) -> None:
        await self.start_publish_diagnostics_task(cast("TDocument", document))

    @_logger.call
    async def start_publish_diagnostics_task(self, document: TDocument) -> None:
        async with self._task_lock:
            self._cancel_entry(self._running_diagnosistcs.get(document.uri, None))

            self._running_diagnosistcs[document.uri] = PublishDiagnosticsEntry(
                document,
                lambda: asyncio.create_task(
                    self.publish_diagnostics(document),
                ),
            )

    @_logger.call
    async def publish_diagnostics(self, document: TDocument) -> None:
        diagnostics: List[Diagnostic] = []
        loop = asyncio.get_event_loop()

        def send_diagnostics(result: Optional[List[Diagnostic]], exception: Optional[BaseException]) -> None:
            nonlocal diagnostics

            if result is not None:
                diagnostics += result
                self.parent.send_notification(
                    "textDocument/publishDiagnostics",
                    PublishDiagnosticsParams(uri=document.uri, version=document.version, diagnostics=diagnostics),
                )
            if exception is not None and type(exception) != asyncio.CancelledError:
                self._logger.exception(exception, exc_info=False)

        def callback(result: Optional[List[Diagnostic]], exception: Optional[BaseException]) -> None:
            loop.call_soon_threadsafe(send_diagnostics, result, exception)

        try:
            await self.collect_diagnostics_event(self, document, result_callback=callback)
        except asyncio.CancelledError:
            raise
