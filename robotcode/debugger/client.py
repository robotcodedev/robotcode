from __future__ import annotations

import asyncio
from typing import Any, Optional, Sequence

from ..jsonrpc2.server import TcpParams
from ..utils.logging import LoggingDescriptor
from .dap_types import Event
from .protocol import DebugAdapterProtocol


class DAPClientProtocol(DebugAdapterProtocol):
    _logger = LoggingDescriptor()

    def __init__(self, parent: DebugAdapterProtocol) -> None:
        super().__init__()
        self.parent = parent
        self.exited = False
        self.terminated = False

    def handle_event(self, message: Event) -> None:
        if message.event == "exited":
            self.exited = True
        elif message.event == "terminated":
            self.terminated = True
        self.parent.send_event(Event(event=message.event, body=message.body))


class DAPClientError(Exception):
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

    async def on_connection_lost(self, sender: Any, exc: Optional[BaseException]) -> None:
        if sender == self._protocol:
            self._protocol = None

    async def connect(self, timeout: float = 5) -> DAPClientProtocol:
        async def wait() -> None:
            while self._protocol is None:
                try:
                    if self.tcp_params.host is not None:
                        if isinstance(self.tcp_params.host, Sequence):
                            host = self.tcp_params.host[0]
                        else:
                            host = self.tcp_params.host
                    else:
                        host = "127.0.0.1"
                    self._transport, protocol = await asyncio.get_running_loop().create_connection(
                        self._create_protocol,
                        host=host,
                        port=self.tcp_params.port,
                    )

                    self._protocol = protocol
                    self._protocol.on_connection_lost.add(self.on_connection_lost)
                except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                    raise
                except ConnectionError:
                    pass

        if self._protocol is not None:
            raise DAPClientError("Client already connected.")

        await asyncio.wait_for(wait(), timeout=timeout)

        return self.protocol

    def _create_protocol(self) -> DAPClientProtocol:
        return DAPClientProtocol(self.parent)

    @property
    def connected(self) -> bool:
        return self._protocol is not None

    @property
    def protocol(self) -> DAPClientProtocol:
        import inspect

        if self._protocol is None:
            raise DAPClientError(f"Client is not connected. {inspect.stack()[1][3]}")
        return self._protocol
