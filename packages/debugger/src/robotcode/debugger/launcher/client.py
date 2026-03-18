from __future__ import annotations

import asyncio
import logging
import weakref
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


class _DAPClientState:
    __slots__ = ("closed", "logger", "loop", "protocol", "transport")

    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.protocol: Optional[DAPClientProtocol] = None
        self.transport: Optional[asyncio.BaseTransport] = None
        self.closed = False


class DAPClient:
    _logger = LoggingDescriptor()

    def __init__(
        self,
        parent: DebugAdapterProtocol,
        tcp_params: TcpParams = TcpParams(None, 0),
    ) -> None:
        self.parent = parent
        self.tcp_params = tcp_params
        self._state = _DAPClientState(
            logging.getLogger(f"{type(self).__module__}.{type(self).__qualname__}"),
        )
        self._finalizer = weakref.finalize(self, DAPClient._finalize_resources, self._state)

    @staticmethod
    def _finalize_resources(state: _DAPClientState) -> None:
        if state.closed or state.transport is None:
            return

        try:
            if state.loop is not None and not state.loop.is_closed() and state.loop.is_running():
                state.loop.call_soon_threadsafe(state.transport.close)
            else:
                state.transport.close()
        except BaseException:
            pass

        state.logger.debug(
            "DAPClient was garbage collected without calling close(); the transport was closed best-effort only.",
        )

    @property
    def _protocol(self) -> Optional[DAPClientProtocol]:
        return self._state.protocol

    @_protocol.setter
    def _protocol(self, value: Optional[DAPClientProtocol]) -> None:
        self._state.protocol = value

    @property
    def _transport(self) -> Optional[asyncio.BaseTransport]:
        return self._state.transport

    @_transport.setter
    def _transport(self, value: Optional[asyncio.BaseTransport]) -> None:
        self._state.transport = value

    @event
    def on_closed(sender) -> None: ...

    @_logger.call
    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._protocol = None

        self._state.closed = True
        self._finalizer.detach()
        self.on_closed(self)

    @_logger.call
    def on_connection_lost(self, sender: Any, exc: Optional[BaseException]) -> None:
        if sender == self._protocol:
            self._protocol = None

    @_logger.call
    async def connect(self, timeout: float = 5) -> DAPClientProtocol:
        async def wait() -> None:
            while self._protocol is None:
                try:
                    current_loop = asyncio.get_running_loop()
                    self._state.loop = current_loop
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
                    ) = await current_loop.create_connection(
                        self._create_protocol,
                        host=host,
                        port=self.tcp_params.port,
                    )

                    self._protocol = protocol
                    self._protocol.on_connection_lost.add(self.on_connection_lost)
                except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                    raise
                except (ConnectionError, OSError):
                    pass
                except BaseException as e:
                    raise DAPClientError(f"Failed to connect to {self.tcp_params.host}:{self.tcp_params.port}") from e

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
