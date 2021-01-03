from asyncio import AbstractEventLoop, CancelledError
import asyncio

from typing import Any, List, Optional

from ...utils.logging import LoggingDescriptor
from ..jsonrpc2.server import JsonRPCServer, JsonRpcServerMode, StdIoParams, TcpParams
from .protocol import LanguageServerProtocol
from .text_document import TextDocument
from .types import Diagnostic, DiagnosticSeverity, Position, Range

__all__ = ["LanguageServer", "TCP_DEFAULT_PORT"]

TCP_DEFAULT_PORT = 6601


class LanguageServer(JsonRPCServer[LanguageServerProtocol]):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        mode: JsonRpcServerMode = JsonRpcServerMode.STDIO,
        stdio_params: StdIoParams = StdIoParams(None, None),
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
        loop: Optional[AbstractEventLoop] = None,
    ):
        super().__init__(
            mode=mode,
            stdio_params=stdio_params,
            tcp_params=tcp_params,
            loop=loop,
        )

    def create_protocol(self) -> LanguageServerProtocol:
        result = LanguageServerProtocol(self)
        result.diagnostics.collect_diagnostics_event.add(self.collect_dummy_diagnostics)
        result.diagnostics.collect_diagnostics_event.add(self.collect_dummy_diagnostics1)
        result.diagnostics.collect_diagnostics_event.add(self.collect_dummy_diagnostics2)
        result.diagnostics.collect_diagnostics_event.add(self.collect_dummy_diagnostics_error)

        return result

    async def collect_dummy_diagnostics(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        self._logger.info("collect_dummy_diagnostics")
        try:
            return [
                Diagnostic(
                    range=Range(start=Position(line=0, character=0), end=Position(line=1, character=0)),
                    message="Hello from Diagnostics",
                    severity=DiagnosticSeverity.ERROR,
                    source="robotcode",
                )
            ]
        except CancelledError:
            self._logger.info("collect_dummy_diagnostics canceled")
            raise
        finally:
            self._logger.info("collect_dummy_diagnostics done")

    async def collect_dummy_diagnostics1(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        try:
            self._logger.info("collect_dummy_diagnostics1")
            await asyncio.sleep(5)
            return [
                Diagnostic(
                    range=Range(start=Position(line=1, character=0), end=Position(line=2, character=0)),
                    message="Hello again from Diagnostics",
                    severity=DiagnosticSeverity.INFORMATION,
                    source="robotcode.intern",
                )
            ]
        except CancelledError:
            self._logger.info("collect_dummy_diagnostics1 canceled")
            raise
        finally:
            self._logger.info("collect_dummy_diagnostics1 done")

    async def collect_dummy_diagnostics2(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        try:
            self._logger.info("collect_dummy_diagnostics2")
            await asyncio.sleep(2)
            return [
                Diagnostic(
                    range=Range(start=Position(line=2, character=0), end=Position(line=3, character=0)),
                    message="Hello again again from Diagnostics",
                    severity=DiagnosticSeverity.WARNING,
                    source="blub",
                )
            ]
        except CancelledError:
            self._logger.info("collect_dummy_diagnostics1 canceled")
            raise
        finally:
            self._logger.info("collect_dummy_diagnostics2 done")

    async def collect_dummy_diagnostics_error(self, sender: Any, document: TextDocument) -> List[Diagnostic]:
        try:
            self._logger.info("collect_dummy_diagnostics_error")
            await asyncio.sleep(3)
            raise Exception("geht nicht")
        except CancelledError:
            self._logger.info("collect_dummy_diagnostics_error canceled")
            raise
        finally:
            self._logger.info("collect_dummy_diagnostics_error done")
