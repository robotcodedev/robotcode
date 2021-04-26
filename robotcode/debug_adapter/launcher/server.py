import asyncio
import os
import threading
from typing import Optional

from ...jsonrpc2.protocol import rpc_method
from ...jsonrpc2.server import JsonRPCServer, JsonRpcServerMode, TcpParams
from ...utils.logging import LoggingDescriptor
from ..protocol import DebugAdapterProtocol
from ..types import (
    ConfigurationDoneArguments,
    DisconnectArguments,
    ExitedEvent,
    ExitedEventBody,
    InitializedEvent,
    SetBreakpointsArguments,
    SetBreakpointsResponseBody,
    TerminateArguments,
    TerminatedEvent,
)

TCP_DEFAULT_PORT = 6612


class LauncherServerProtocol(DebugAdapterProtocol):
    _logger = LoggingDescriptor()

    def __init__(self) -> None:
        super().__init__()
        self._initialized = False
        self._connect_lock = threading.RLock()
        self._connected = False
        self._sigint_signaled = False

        self._exited_lock = asyncio.Lock()
        self._exited = False

        self._terminated_lock = asyncio.Lock()
        self._terminated = False

        self._received_configuration_done_lock = asyncio.Lock()
        self._received_configuration_done = True

    @property
    def connected(self) -> bool:
        with self._connect_lock:
            return self._connected

    @property
    async def exited(self) -> bool:
        async with self._exited_lock:
            return self._exited

    @property
    async def terminated(self) -> bool:
        async with self._terminated_lock:
            return self._terminated

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
                await asyncio.sleep(0.01)

        await asyncio.wait_for(wait(), timeout)

        return self.read_transport is not None and self.write_transport is not None

    @_logger.call
    async def initialized(self) -> None:
        await self.send_event_async(InitializedEvent())

    @_logger.call
    async def exit(self, exit_code: int) -> None:
        async with self._exited_lock:
            await self.send_event_async(ExitedEvent(body=ExitedEventBody(exit_code=exit_code)))
            self._exited = True

    @_logger.call
    async def terminate(self) -> None:
        async with self._terminated_lock:
            await self.send_event_async(TerminatedEvent())
            self._terminated = True

    @rpc_method(name="terminate", param_type=TerminateArguments)
    async def _terminate(self, arguments: Optional[TerminateArguments] = None) -> None:
        import signal

        if not self._sigint_signaled:
            self._logger.info("Send SIGINT to process")
            signal.raise_signal(signal.SIGINT)
            self._sigint_signaled = True
        else:
            self._logger.info("Send SIGTERM to process")
            signal.raise_signal(signal.SIGTERM)

    @rpc_method(name="disconnect", param_type=DisconnectArguments)
    async def _disconnect(self, arguments: Optional[DisconnectArguments] = None) -> None:
        if not (await self.exited) or not (await self.terminated):
            if arguments is None or arguments.terminate_debuggee is None or arguments.terminate_debuggee:
                os._exit(-1)

    @rpc_method(name="setBreakpoints", param_type=SetBreakpointsArguments)
    async def _set_breakpoints(self, arguments: SetBreakpointsArguments) -> SetBreakpointsResponseBody:
        return SetBreakpointsResponseBody(breakpoints=[])

    @rpc_method(name="configurationDone", param_type=ConfigurationDoneArguments)
    async def _configuration_done(self, arguments: Optional[ConfigurationDoneArguments] = None) -> None:
        async with self._received_configuration_done_lock:
            self._received_configuration_done = True

    @_logger.call
    async def wait_for_configuration_done(self, timeout: float = 5) -> bool:
        async def wait() -> None:
            while True:
                async with self._received_configuration_done_lock:
                    if self._received_configuration_done:
                        break
                await asyncio.sleep(0.01)

        await asyncio.wait_for(wait(), timeout)

        return self._received_configuration_done


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
