import asyncio
import threading
from typing import Optional

from ...jsonrpc2.protocol import rpc_method
from ...jsonrpc2.server import JsonRPCServer, JsonRpcServerMode, TcpParams
from ...utils.logging import LoggingDescriptor
from ..protocol import DebugAdapterProtocol
from ..types import TerminateArguments

TCP_DEFAULT_PORT = 6612


class LauncherServerProtocol(DebugAdapterProtocol):
    _logger = LoggingDescriptor()

    def __init__(self) -> None:
        super().__init__()
        self._initialized = False
        self._connect_lock = threading.RLock()
        self._connected = False

    @property
    def connected(self) -> bool:
        with self._connect_lock:
            return self._connected

    @_logger.call
    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        if self.connected:
            raise ConnectionError("Protocol already connected, only one conntection allowed.")

        super().connection_made(transport)
        with self._connect_lock:
            self._connected = self.read_transport is not None and self.write_transport is not None

    @_logger.call
    def connection_lost(self, exc: Optional[BaseException]) -> None:
        super().connection_lost(exc)
        with self._connect_lock:
            self._connected = False

    @_logger.call
    async def wait_for_client(self, timeout: float = 5) -> bool:
        async def wait() -> None:
            while self.read_transport is None or self.write_transport is None:
                await asyncio.sleep(0.05)

        await asyncio.wait_for(wait(), timeout)

        return self.read_transport is not None and self.write_transport is not None

    @rpc_method(name="terminate", param_type=TerminateArguments)
    @_logger.call
    async def _terminate(self, arguments: Optional[TerminateArguments] = None) -> None:
        import signal

        signal.raise_signal(signal.SIGINT)


class LaucherServer(JsonRPCServer[LauncherServerProtocol]):
    def __init__(
        self,
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
    ):
        super().__init__(
            mode=JsonRpcServerMode.TCP,
            tcp_params=tcp_params,
        )
        self.protocol = LauncherServerProtocol()

    def create_protocol(self) -> LauncherServerProtocol:
        return self.protocol
