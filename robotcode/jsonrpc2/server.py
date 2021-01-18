import abc
import asyncio
import concurrent.futures
import io
import sys
from enum import Enum
from types import TracebackType
from typing import BinaryIO, Callable, Generic, Literal, NamedTuple, Optional, Type, cast

from ..utils.logging import LoggingDescriptor
from .protocol import JsonRPCException, JsonRPCProtocol, TProtocol

__all__ = ["StdOutTransportAdapter", "JsonRpcServerMode", "TcpParams", "JsonRPCServer"]


class StdOutTransportAdapter(asyncio.Transport):
    def __init__(self, rfile: BinaryIO, wfile: BinaryIO) -> None:
        super().__init__()
        self.rfile = rfile
        self.wfile = wfile

    def close(self) -> None:
        self.rfile.close()
        self.wfile.close()

    def write(self, data: bytes) -> None:
        self.wfile.write(data)
        self.wfile.flush()


class JsonRpcServerMode(Enum):
    STDIO = "stdio"
    TCP = "tcp"


class TcpParams(NamedTuple):
    host: Optional[str] = None
    port: int = 0


class JsonRPCServer(Generic[TProtocol], abc.ABC):
    def __init__(
        self,
        mode: JsonRpcServerMode = JsonRpcServerMode.STDIO,
        tcp_params: TcpParams = TcpParams(None, 0),
    ):
        self.mode = mode
        self.tcp_params = tcp_params

        self._run_func: Optional[Callable[[], None]] = None
        self._server: Optional[asyncio.AbstractServer] = None

        self._stop_event: Optional[asyncio.Event] = None

        self.loop = asyncio.get_event_loop()

        self.stdio_future: Optional[concurrent.futures.Future] = None

        self.loop.set_debug(True)

    @property
    def __del__(self) -> None:
        self.close()

    _logger = LoggingDescriptor()

    @_logger.call
    def start(self) -> None:
        if self.mode == JsonRpcServerMode.STDIO:
            self.start_stdio()
        elif self.mode == JsonRpcServerMode.TCP:
            self.start_tcp(self.tcp_params.host, self.tcp_params.port)
        else:
            raise JsonRPCException(f"Unknown server mode {self.mode}")

    @_logger.call
    def close(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()

        if self._server:
            self._server.close()
            self.loop.run_until_complete(self._server.wait_closed())
            self._server = None

        if self.stdio_future is not None:
            self.stdio_future.cancel()

        if not self.loop.is_closed():
            self.loop.close()

    def __enter__(self) -> "JsonRPCServer[TProtocol]":
        self.start()
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Literal[False]:
        self.close()
        return False

    @abc.abstractmethod
    def create_protocol(self) -> TProtocol:
        ...

    def close_protocol(self, protocol: TProtocol) -> None:
        if self.mode == JsonRpcServerMode.STDIO and self._stop_event is not None:
            self._stop_event.set()

    @_logger.call
    def start_stdio(self) -> None:
        self.mode = JsonRpcServerMode.STDIO

        async def aio_read(rfile: BinaryIO, protocol: JsonRPCProtocol) -> None:
            """Reads data from stdin in separate thread (asynchronously)."""

            def read_unbuffered() -> bytes:
                return rfile.read(1)

            def read_buffered() -> bytes:
                return cast(io.BufferedReader, rfile).read1(500)

            read_func = read_unbuffered
            if isinstance(rfile, io.BufferedReader):
                read_func = read_buffered

            while self._stop_event is not None and not self._stop_event.is_set() and not rfile.closed:
                protocol.data_received(await self.loop.run_in_executor(None, read_func))

        def threading_read(rfile: BinaryIO, protocol: JsonRPCProtocol) -> None:
            def read_unbuffered() -> bytes:
                return rfile.read(1)

            def read_buffered() -> bytes:
                return cast(io.BufferedReader, rfile).read1(500)

            read_func = read_unbuffered
            if isinstance(rfile, io.BufferedReader):
                read_func = read_buffered

            while self._stop_event is not None and not self._stop_event.is_set() and not rfile.closed:
                self.loop.call_soon_threadsafe(protocol.data_received, read_func())

        transport = StdOutTransportAdapter(sys.stdin.buffer, sys.stdout.buffer)

        protocol = self.create_protocol()

        protocol.connection_made(transport)

        def run_io() -> None:
            self._stop_event = asyncio.Event()

            future = self.loop.run_in_executor(None, threading_read, sys.stdin.buffer, protocol)

            self.loop.run_until_complete(future)

        self._run_func = run_io

    @_logger.call
    def start_tcp(self, host: Optional[str] = None, port: int = 0) -> None:
        self.mode = JsonRpcServerMode.TCP

        self._server = self.loop.run_until_complete(self.loop.create_server(lambda: self.create_protocol(), host, port))
        self._run_func = self.loop.run_forever

    @_logger.call
    def run(self) -> None:
        if self._run_func is None:
            self._logger.warning("server is not started.")
            return
        self._run_func()
