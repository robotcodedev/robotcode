from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, cast

from ....utils.async_tools import CancelationToken, async_tasking_event_iterator
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ..language import language_id, language_id_filter
from ..lsp_types import Diagnostic, DocumentUri, PublishDiagnosticsParams
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart

__all__ = ["DiagnosticsProtocolPart", "DiagnosticsResult"]

DIAGNOSTICS_DEBOUNCE = 0.75


class PublishDiagnosticsEntry:
    _logger = LoggingDescriptor()

    def __init__(
        self,
        uri: Uri,
        cancelation_token: CancelationToken,
        task_factory: Callable[..., asyncio.Task[Any]],
        done_callback: Callable[[PublishDiagnosticsEntry], Any],
    ) -> None:

        self.uri = uri

        self._task_factory = task_factory
        self.done_callback = done_callback

        self._task: Optional[asyncio.Task[Any]] = None

        self.cancel_token = cancelation_token
        self.done = False

        @PublishDiagnosticsEntry._logger.call
        def create_task() -> None:
            self._task = self._task_factory()

            if self._task is not None:
                self._task.set_name(f"Diagnostics for {self.uri}")

                def _done(t: asyncio.Task[Any]) -> None:
                    self._task = None
                    self.done = True
                    self.done_callback(self)

                self._task.add_done_callback(_done)

        self._timer_handle: asyncio.TimerHandle = asyncio.get_event_loop().call_later(DIAGNOSTICS_DEBOUNCE, create_task)

    def __del__(self) -> None:
        if self.task is not None:
            self.cancel(_from_del=True)

    @property
    def task(self) -> Optional[asyncio.Task[Any]]:
        return self._task

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"{type(self)}(document={repr(self.uri)}, task={repr(self.task)}, done={self.done})"

    @_logger.call(condition=lambda self, _from_del=False: not _from_del)
    def cancel(self, *, _from_del: Optional[bool] = False) -> Optional[asyncio.Task[None]]:
        self._timer_handle.cancel()

        if self.task is None:
            return None

        self.cancel_token.cancel()

        async def cancel() -> None:
            if self.task is None:
                return

            t = self.task
            self._task = None
            if not t.done():
                t.cancel()
                try:
                    await t
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException:
                    pass

        return asyncio.create_task(cancel())


@dataclass
class DiagnosticsResult:
    key: Any
    diagnostics: Optional[List[Diagnostic]] = None


class DiagnosticsProtocolPart(LanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, protocol: LanguageServerProtocol) -> None:
        super().__init__(protocol)

        self._running_diagnostics: Dict[Uri, PublishDiagnosticsEntry] = {}
        self._task_lock = asyncio.Lock()

        self.parent.on_connection_lost.add(self.on_connection_lost)
        self.parent.on_shutdown.add(self.on_shutdown)
        self.parent.documents.did_open.add(self.on_did_open)
        self.parent.documents.did_change.add(self.on_did_change)
        self.parent.documents.did_close.add(self.on_did_close)
        self.parent.documents.did_save.add(self.on_did_save)

    @async_tasking_event_iterator
    async def collect(
        sender, document: TextDocument, cancelation_token: CancelationToken
    ) -> DiagnosticsResult:  # NOSONAR
        ...

    @_logger.call
    async def on_connection_lost(self, sender: Any, exc: Optional[BaseException]) -> None:
        await self._cancel_all_tasks()

    @_logger.call
    async def on_shutdown(self, sender: Any) -> None:
        await self._cancel_all_tasks()

    def __del__(self) -> None:
        if len(self._running_diagnostics) > 0:
            self._logger.warning("there are running tasks")

    @_logger.call
    async def _cancel_all_tasks(self) -> None:
        tasks_copy = None
        async with self._task_lock:
            tasks_copy = self._running_diagnostics.copy()
            self._running_diagnostics = {}
        if tasks_copy is not None:
            for v in tasks_copy.values():
                self._cancel_entry(v)

    @_logger.call(condition=lambda self, entry: entry is not None)
    async def _cancel_entry(self, entry: Optional[PublishDiagnosticsEntry]) -> None:
        if entry is None:
            return
        if not entry.done:
            cancel_task = entry.cancel()
            if cancel_task is not None:
                await cancel_task

    @language_id("robotframework")
    @_logger.call
    async def on_did_open(self, sender: Any, document: TextDocument) -> None:
        await self.start_publish_diagnostics_task(document)

    @language_id("robotframework")
    @_logger.call
    async def on_did_save(self, sender: Any, document: TextDocument) -> None:
        await self.start_publish_diagnostics_task(document)

    @language_id("robotframework")
    @_logger.call
    async def on_did_close(self, sender: Any, document: TextDocument) -> None:
        async with self._task_lock:
            self._cancel_entry(self._running_diagnostics.get(document.uri, None))

    @_logger.call
    async def on_did_change(self, sender: Any, document: TextDocument) -> None:
        await self.start_publish_diagnostics_task(document)

    @_logger.call
    def _delete_entry(self, e: PublishDiagnosticsEntry) -> None:
        if e.uri in self._running_diagnostics and self._running_diagnostics[e.uri] == e:
            self._running_diagnostics.pop(e.uri, None)

    @_logger.call
    async def start_publish_diagnostics_task(self, document: TextDocument) -> None:
        await self._cancel_entry(self._running_diagnostics.get(document.uri, None))

        async with self._task_lock:
            cancelation_token = CancelationToken()
            self._running_diagnostics[document.uri] = PublishDiagnosticsEntry(
                document.uri,
                cancelation_token,
                lambda: asyncio.create_task(
                    self.publish_diagnostics(document.document_uri, cancelation_token),
                ),
                self._delete_entry,
            )

    @_logger.call
    async def publish_diagnostics(self, document_uri: DocumentUri, cancelation_token: CancelationToken) -> None:
        document = self.parent.documents.get(document_uri, None)
        if document is None:
            return

        diagnostics: Dict[Any, List[Diagnostic]] = document.get_data(self, {})

        collected_keys: List[Any] = []

        async for result_any in self.collect(
            self,
            document,
            cancelation_token,
            callback_filter=language_id_filter(document),
            return_exceptions=True,
        ):
            if cancelation_token.canceled:
                break

            result = cast(DiagnosticsResult, result_any)

            if isinstance(result, BaseException):
                # if not isinstance(result, asyncio.CancelledError):
                self._logger.exception(result, exc_info=result)
            else:

                diagnostics[result.key] = result.diagnostics if result.diagnostics else []
                collected_keys.append(result.key)

                asyncio.get_event_loop().call_soon(
                    self.parent.send_notification,
                    "textDocument/publishDiagnostics",
                    PublishDiagnosticsParams(
                        uri=document.document_uri,
                        version=document.version,
                        diagnostics=[e for e in itertools.chain(*diagnostics.values())],
                    ),
                )

        for k in set(diagnostics.keys()) - set(collected_keys):
            diagnostics.pop(k)

        document.set_data(self, diagnostics)
