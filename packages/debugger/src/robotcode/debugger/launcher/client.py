from __future__ import annotations

import asyncio
from typing import Any, Optional, Sequence

from robotcode.core.event import event
from robotcode.core.types import TcpParams
from robotcode.core.utils.logging import LoggingDescriptor

from ..dap_types import Event
from ..protocol import DebugAdapterProtocol


class DAPClientProtocol(DebugAdapterProtocol):
    _logger = LoggingDescriptor()

    def __init__(self, parent: DebugAdapterProtocol, client: DAPClient) -> None:
        super().__init__()
        self.parent = parent
        self.client = client
        self.exited = False
        self.terminated = False

    @_logger.call
    def handle_event(self, message: Event) -> None:
        if message.event == "exited":
            self.exited = True

        elif message.event == "terminated":
            self.terminated = True
            if self.exited:
                self.client.close()

        self.parent.send_event(Event(event=message.event, body=message.body))


class DAPClientError(Exception):
    pass


class DAPClient:
    _logger = LoggingDescriptor()

    def __init__(
        self,
        parent: DebugAdapterProtocol,
        tcp_params: TcpParams = TcpParams(None, 0),
    ) -> None:
        self.parent = parent
        self.tcp_params = tcp_params
        self._protocol: Optional[DAPClientProtocol] = None
        self._transport: Optional[asyncio.BaseTransport] = None

    @event
    def on_closed(sender) -> None: ...

    @_logger.call
    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._protocol = None

        self.on_closed(self)

    def __del__(self) -> None:
        self.close()

    @_logger.call
    def on_connection_lost(self, sender: Any, exc: Optional[BaseException]) -> None:
        if sender == self._protocol:
            self._protocol = None

    @_logger.call
    async def connect(self, timeout: float = 5) -> DAPClientProtocol:
        async def wait() -> None:
            while self._protocol is None:
                try:
                    if self.tcp_params.host is not None:
                        if isinstance(self.tcp_params.host, Sequence):
                            host = self.tcp_params.host[0]
                        else:
                            host = self.tcp_params.host  # type: ignore
                    else:
                        host = "127.0.0.1"
                    (
                        self._transport,
                        protocol,
                    ) = await asyncio.get_running_loop().create_connection(
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
        return DAPClientProtocol(self.parent, self)

    @property
    def connected(self) -> bool:
        return self._protocol is not None

    @property
    def protocol(self) -> DAPClientProtocol:
        if self._protocol is None:
            raise DAPClientError("Client is not connected.")
        return self._protocol
