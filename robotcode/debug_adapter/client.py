from __future__ import annotations

import asyncio
from typing import Optional, cast

from ..jsonrpc2.server import TcpParams
from ..utils.logging import LoggingDescriptor
from .protocol import DebugAdapterProtocol
from .types import Event


class DAPClientProtocol(DebugAdapterProtocol):
    _logger = LoggingDescriptor()

    def __init__(self, parent: DebugAdapterProtocol) -> None:
        super().__init__()
        self.parent = parent

    async def handle_event(self, message: Event) -> None:
        self.parent.send_event(Event(event=message.event, body=message.body))


class ClientNotConnectedError(Exception):
    pass


class DAPClient:
    def __init__(self, parent: DebugAdapterProtocol, tcp_params: TcpParams = TcpParams(None, 0)) -> None:
        self.parent = parent
        self.tcp_params = tcp_params
        self._protocol: Optional[DAPClientProtocol] = None
        self._transport: Optional[asyncio.BaseTransport] = None

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._protocol = None

    def __del__(self) -> None:
        self.close()

    async def connect(self, timeout: float = 5) -> DAPClientProtocol:
        async def wait() -> None:
            while self._protocol is None:
                try:
                    self._transport, protocol = await asyncio.get_running_loop().create_connection(
                        self._create_protocol,
                        host=self.tcp_params.host if self.tcp_params.host is not None else "127.0.0.1",
                        port=self.tcp_params.port,
                    )

                    self._protocol = cast(DAPClientProtocol, protocol)
                except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                    raise
                except ConnectionError:
                    pass

        await asyncio.wait_for(wait(), timeout=timeout)

        return self.protocol

    def _create_protocol(self) -> DAPClientProtocol:
        return DAPClientProtocol(self.parent)

    @property
    def protocol(self) -> DAPClientProtocol:
        if self._protocol is None:
            raise ClientNotConnectedError("Debug Adapter Client is not connected.")
        return self._protocol
