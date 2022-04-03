from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, cast

from ....utils.async_tools import (
    Lock,
    async_tasking_event_iterator,
    check_canceled,
    create_sub_task,
    run_coroutine_in_thread,
)
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ..decorators import language_id, language_id_filter
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
        version: Optional[int],
        factory: Callable[..., asyncio.Future[Any]],
        done_callback: Callable[[PublishDiagnosticsEntry], Any],
        no_wait: bool = False,
    ) -> None:

        self.uri = uri
        self.version = version

        self._factory = factory
        self.done_callback = done_callback

        self._future: Optional[asyncio.Future[Any]] = None

        self.done = False
        self.no_wait = no_wait

        def _done(t: asyncio.Future[Any]) -> None:
            self.done = True
            self.done_callback(self)

        self._future = create_sub_task(self._wait_and_run())
        self._future.add_done_callback(_done)

    async def _wait_and_run(self) -> None:
        if not self.no_wait:
            await asyncio.sleep(DIAGNOSTICS_DEBOUNCE)

        await self._factory()

    def __del__(self) -> None:
        if not self.done:
            try:
                if asyncio.get_running_loop():
                    create_sub_task(self.cancel())
            except RuntimeError:
                pass

    @property
    def future(self) -> Optional[asyncio.Future[Any]]:
        return self._future

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"{type(self)}(document={repr(self.uri)}, task={repr(self.future)}, done={self.done})"

    @_logger.call
    async def cancel(self) -> None:
        if self.future is None:
            return

        self.done = True

        if not self.future.done() and not self.future.cancelled():
            self.future.cancel()
            try:
                await self.future
            except (asyncio.CancelledError):
                pass
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as ex:
                self._logger.exception(ex)
                raise
            finally:
                self._future = None


@dataclass
class DiagnosticsResult:
    key: Any
    diagnostics: Optional[List[Diagnostic]] = None


class DiagnosticsProtocolPart(LanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, protocol: LanguageServerProtocol) -> None:
        super().__init__(protocol)

        self._running_diagnostics: Dict[Uri, PublishDiagnosticsEntry] = {}
        self._tasks_lock = Lock()

        self.parent.on_connection_lost.add(self.on_connection_lost)
        self.parent.on_shutdown.add(self.on_shutdown)
        self.parent.documents.did_open.add(self.on_did_open)
        self.parent.documents.did_change.add(self.on_did_change)
        self.parent.documents.did_close.add(self.on_did_close)
        self.parent.documents.did_save.add(self.on_did_save)

    @async_tasking_event_iterator
    async def collect(sender, document: TextDocument) -> DiagnosticsResult:  # NOSONAR
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
        async with self._tasks_lock:
            tasks_copy = self._running_diagnostics.copy()
            self._running_diagnostics = {}
        if tasks_copy is not None:
            for v in tasks_copy.values():
                await self._cancel_entry(v)

    @_logger.call(condition=lambda self, entry: entry is not None)
    async def _cancel_entry(self, entry: Optional[PublishDiagnosticsEntry]) -> None:
        if entry is None:
            return
        if not entry.done:
            await entry.cancel()

    @language_id("robotframework")
    @_logger.call
    async def on_did_open(self, sender: Any, document: TextDocument) -> None:
        create_sub_task(self.start_publish_diagnostics_task(document))

    @language_id("robotframework")
    @_logger.call
    async def on_did_save(self, sender: Any, document: TextDocument) -> None:
        create_sub_task(self.start_publish_diagnostics_task(document))

    @language_id("robotframework")
    @_logger.call
    async def on_did_close(self, sender: Any, document: TextDocument) -> None:
        try:
            await self._cancel_entry(self._running_diagnostics.get(document.uri, None))
        finally:
            self.parent.send_notification(
                "textDocument/publishDiagnostics",
                PublishDiagnosticsParams(
                    uri=document.document_uri,
                    version=document._version,
                    diagnostics=[],
                ),
            )

    @_logger.call
    async def on_did_change(self, sender: Any, document: TextDocument) -> None:
        create_sub_task(self.start_publish_diagnostics_task(document))

    @_logger.call
    def _delete_entry(self, e: PublishDiagnosticsEntry) -> None:
        if e.uri in self._running_diagnostics and self._running_diagnostics[e.uri] == e:
            self._running_diagnostics.pop(e.uri, None)

    @_logger.call
    async def start_publish_diagnostics_task(self, document: TextDocument, no_wait: bool = False) -> None:
        async with self._tasks_lock:
            entry = self._running_diagnostics.get(document.uri, None)

        if entry is not None and entry.version == document.version:
            return

        await self._cancel_entry(entry)

        self._running_diagnostics[document.uri] = PublishDiagnosticsEntry(
            document.uri,
            document.version,
            lambda: run_coroutine_in_thread(self.publish_diagnostics, document.document_uri),
            # lambda: create_sub_task(self.publish_diagnostics(document.document_uri)),
            self._delete_entry,
            no_wait,
        )

    @_logger.call
    async def publish_diagnostics(self, document_uri: DocumentUri) -> None:
        document = await self.parent.documents.get(document_uri)
        if document is None:
            return

        diagnostics: Dict[Any, List[Diagnostic]] = document.get_data(self, {})

        collected_keys: List[Any] = []

        async for result_any in self.collect(
            self,
            document,
            callback_filter=language_id_filter(document),
            return_exceptions=True,
        ):
            await check_canceled()

            result = cast(DiagnosticsResult, result_any)

            if isinstance(result, BaseException):
                if not isinstance(result, asyncio.CancelledError):
                    self._logger.exception(result, exc_info=result)
            else:

                diagnostics[result.key] = result.diagnostics if result.diagnostics else []
                collected_keys.append(result.key)

                asyncio.get_event_loop().call_soon(
                    self.parent.send_notification,
                    "textDocument/publishDiagnostics",
                    PublishDiagnosticsParams(
                        uri=document.document_uri,
                        version=document._version,
                        diagnostics=[e for e in itertools.chain(*diagnostics.values())],
                    ),
                )

        for k in set(diagnostics.keys()) - set(collected_keys):
            diagnostics.pop(k)

        document.set_data(self, diagnostics)
