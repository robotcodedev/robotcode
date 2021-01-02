import asyncio
import logging
from typing import TYPE_CHECKING, Dict

from ....utils.logging import LoggingDescriptor
from ...jsonrpc2 import GenericJsonRPCProtocolPart
from .documents import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

__all__ = ["DiagnosticsProtocolPart"]


class DiagnosticsProtocolPart(GenericJsonRPCProtocolPart["LanguageServerProtocol"]):
    _logger = LoggingDescriptor()

    def __init__(self, protocol: "LanguageServerProtocol") -> None:
        super().__init__(protocol)
        self.protocol.shutdown_event += self.on_shutdown
        self.protocol.documents.did_open_event += self.on_did_open
        self.protocol.documents.did_change_event += self.on_did_change
        self.protocol.documents.did_close_event += self.on_did_close
        self.running_diagnosistcs_tasks: Dict[TextDocument, asyncio.Task] = {}
        self.task_lock = asyncio.Lock()

    def on_shutdown(self, sender):
        self.cancel_all_tasks()

    def __del__(self):
        self.cancel_all_tasks()

    def cancel_all_tasks(self):
        tasks_copy = self.running_diagnosistcs_tasks.copy()
        self.running_diagnosistcs_tasks = {}
        for task in tasks_copy.values():
            task.cancel()

    @_logger.call(level=logging.INFO)
    async def on_did_open(self, sender, document: TextDocument):
        await self.start_collect_diagnostics_task(document)

    @_logger.call(level=logging.INFO)
    async def on_did_close(self, sender, document: TextDocument):
        pass

    @_logger.call(level=logging.INFO)
    async def on_did_change(self, sender, document: TextDocument):
        await self.start_collect_diagnostics_task(document)

    async def start_collect_diagnostics_task(self, document: TextDocument):
        if self.protocol.server is None:
            return

        async def done_callback(t):
            async with self.task_lock:
                self.running_diagnosistcs_tasks.pop(document, None)
            self._logger.info("task done")

        def call_done_callback(t):
            asyncio.run_coroutine_threadsafe(done_callback(t), asyncio.get_running_loop())

        if document in self.running_diagnosistcs_tasks and not self.running_diagnosistcs_tasks[document].done():
            self.running_diagnosistcs_tasks[document].cancel()
            try:
                await self.running_diagnosistcs_tasks[document]
            except asyncio.CancelledError:
                self._logger.info("task was canceled")
                pass

        async with self.task_lock:
            task = self.protocol.server.loop.create_task(
                self.collect_diagnostics(document),
                name=f"collect diagnostics for {document}",
            )
            task.add_done_callback(call_done_callback)
            self.running_diagnosistcs_tasks[document] = task
        return task

    @_logger.call(level=logging.INFO)
    async def collect_diagnostics(self, document: TextDocument):

        i = 0
        try:
            while True:
                await asyncio.sleep(1)

                self._logger.info(f"{document} dumum {i}")
                i += 1
                if i == 100:
                    break
        except asyncio.CancelledError as e:
            self._logger.info("canceled " + str(e))
            raise
