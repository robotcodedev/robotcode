import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from ....utils.logging import LoggingDescriptor
from ...jsonrpc2.protocol import JsonRPCProtocol, GenericJsonRPCProtocolPart
from ..text_document import TextDocument
from ..types import DocumentUri

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

__all__ = ["DiagnosticsProtocolPart"]


class DiagnosticsProtocolPart(GenericJsonRPCProtocolPart['LanguageServerProtocol']):
    _logger = LoggingDescriptor()

    def __init__(self, protocol: "LanguageServerProtocol") -> None:
        super().__init__(protocol)

        self._running_diagnosistcs_tasks: Dict[DocumentUri, Tuple[asyncio.Task[Any], Optional[int]]] = {}
        self._task_lock = asyncio.Lock()
        self._start_lock_lock = asyncio.Lock()

        self.parent.connection_lost_event.add(self.on_connection_lost)
        self.parent.shutdown_event.add(self.on_shutdown)
        self.parent.documents.did_open_event.add(self.on_did_open)
        self.parent.documents.did_change_event.add(self.on_did_change)
        self.parent.documents.did_close_event.add(self.on_did_close)
        self.parent.documents.did_save_event.add(self.on_did_save)

    @_logger.call
    async def on_connection_lost(self, sender: JsonRPCProtocol, ex: BaseException) -> None:
        await self.cancel_all_tasks()

    @_logger.call
    async def on_shutdown(self, sender: 'LanguageServerProtocol') -> None:
        await self.cancel_all_tasks()

    def __del__(self) -> None:
        if len(self._running_diagnosistcs_tasks) > 0:
            self._logger.warning("there are running tasks")

    @_logger.call
    async def cancel_all_tasks(self) -> None:
        tasks_copy = None
        async with self._task_lock:
            tasks_copy = self._running_diagnosistcs_tasks.copy()
            self._running_diagnosistcs_tasks = {}
        if tasks_copy is not None:
            for task, _ in tasks_copy.values():
                task.cancel()

    @_logger.call(level=logging.INFO)
    async def on_did_open(self, sender: Any, document: TextDocument) -> None:
        await self.start_collect_diagnostics_task(document)

    @_logger.call
    async def on_did_save(self, sender: Any, document: TextDocument) -> None:
        await self.start_collect_diagnostics_task(document)

    @_logger.call
    async def on_did_close(self, sender: Any, document: TextDocument) -> None:
        pass

    @_logger.call(level=logging.INFO)
    async def on_did_change(self, sender: Any, document: TextDocument) -> None:
        await self.start_collect_diagnostics_task(document)

    @_logger.call
    async def start_collect_diagnostics_task(self, document: TextDocument) -> None:
        document = document.copy()

        async def done_callback(t: asyncio.Task[Any]) -> None:
            async with self._task_lock:
                if self._running_diagnosistcs_tasks.get(document.uri, (None, None))[0] == t:
                    self._running_diagnosistcs_tasks.pop(document.uri, None)

        def call_done_callback(t: asyncio.Task[Any]) -> None:
            asyncio.ensure_future(done_callback(t))

        # async with self._start_lock_lock:
        if self.parent.server is None:
            return

        async with self._task_lock:

            (running_task, version) = self._running_diagnosistcs_tasks.get(document.uri, (None, None))

            if document.version == version:
                self._logger.info(f"allready run diagnostics task for document {document} and version {version}")
                return

            if running_task is not None and not running_task.done():
                self._logger.info(f"cancel task {document} version {version}")
                running_task.cancel()
                try:
                    await running_task
                except asyncio.CancelledError:
                    pass
                except BaseException:
                    pass
            else:
                pass

            task = asyncio.create_task(
                self.collect_diagnostics(document),
                # name=f"collect diagnostics for {document}",
            )

            self._logger.info(f"create task {document} version {version}")
            task.add_done_callback(call_done_callback)
            self._running_diagnosistcs_tasks[document.uri] = (task, document.version)

    @_logger.call
    async def collect_diagnostics(self, document: TextDocument) -> None:
        self._logger.info(f"start {document}")
        i = 0
        try:
            while True:
                await asyncio.sleep(1)

                # self._logger.info(f"{document} dumum {i}")
                i += 1
                if i == 5:
                    break
        except asyncio.CancelledError:
            self._logger.info(f"canceled {document}")
            raise

        self._logger.info(f"done {document}")
