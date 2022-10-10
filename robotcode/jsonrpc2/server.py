import abc
import asyncio
import io
import sys
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from types import TracebackType
from typing import (
    BinaryIO,
    Callable,
    Coroutine,
    Generic,
    NamedTuple,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
)

from ..utils.logging import LoggingDescriptor
from .protocol import JsonRPCException

__all__ = ["JsonRpcServerMode", "TcpParams", "JsonRPCServer"]

TProtocol = TypeVar("TProtocol", bound=asyncio.Protocol)


class NotSupportedError(Exception):
    pass


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
    SOCKET = "socket"
    PIPE = "pipe"


class TcpParams(NamedTuple):
    host: Union[str, Sequence[str], None] = None
    port: int = 0


class JsonRPCServer(Generic[TProtocol], abc.ABC):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        mode: JsonRpcServerMode = JsonRpcServerMode.STDIO,
        tcp_params: TcpParams = TcpParams(None, 0),
        pipe_name: Optional[str] = None,
    ):
        self.mode = mode
        self.tcp_params = tcp_params
        self.pipe_name = pipe_name

        self._run_func: Optional[Callable[[], None]] = None
        self._serve_func: Optional[Callable[[], Coroutine[None, None, None]]] = None
        self._server: Optional[asyncio.AbstractServer] = None

        self._stdio_stop_event: Optional[asyncio.Event] = None

        self._in_closing = False
        self._closed = False

        self.loop = asyncio.get_event_loop()
        if self.loop is not None:
            self.loop.slow_callback_duration = 10

    def __del__(self) -> None:
        self.close()

    @_logger.call
    def start(self) -> None:
        if self.mode == JsonRpcServerMode.STDIO:
            self.start_stdio()
        elif self.mode == JsonRpcServerMode.TCP:
            self.loop.run_until_complete(self.start_tcp(self.tcp_params.host, self.tcp_params.port))
        elif self.mode == JsonRpcServerMode.PIPE:
            self.start_pipe(self.pipe_name)
        elif self.mode == JsonRpcServerMode.SOCKET:
            self.start_socket(self.tcp_params.port)
        else:
            raise JsonRPCException(f"Unknown server mode {self.mode}")

    @_logger.call
    async def start_async(self) -> None:
        if self.mode == JsonRpcServerMode.TCP:
            await self.start_tcp(self.tcp_params.host, self.tcp_params.port)
        else:
            raise JsonRPCException(f"Unsupported server mode {self.mode}")

    @_logger.call
    def _close(self) -> None:
        if self._stdio_stop_event is not None:
            self._stdio_stop_event.set()

        if self._server and self._server.is_serving():
            self._server.close()

    @_logger.call
    def close(self) -> None:
        if self._in_closing or self._closed:
            return

        self._in_closing = True
        try:
            self._close()
        finally:
            self._in_closing = False
            self._closed = True

    @_logger.call
    async def close_async(self) -> None:
        if self._in_closing or self._closed:
            return

        self._in_closing = True
        try:
            self._close()
            if self._server is not None:
                await self._server.wait_closed()
        finally:
            self._in_closing = False
            self._closed = True

    async def __aenter__(self) -> "JsonRPCServer[TProtocol]":
        await self.start_async()
        return self

    async def __aexit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> bool:
        await self.close_async()
        return False

    def __enter__(self) -> "JsonRPCServer[TProtocol]":
        self.start()
        return self

    def __exit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()

    @abc.abstractmethod
    def create_protocol(self) -> TProtocol:
        ...

    stdio_executor: Optional[ThreadPoolExecutor] = None

    @_logger.call
    def start_stdio(self) -> None:
        self.mode = JsonRpcServerMode.STDIO

        transport = StdOutTransportAdapter(sys.__stdin__.buffer, sys.__stdout__.buffer)

        protocol = self.create_protocol()

        def run_io_nonblocking() -> None:
            self._stdio_stop_event = asyncio.Event()

            async def aio_readline(rfile: BinaryIO, protocol: asyncio.Protocol) -> None:
                protocol.connection_made(transport)

                def run() -> None:
                    while (
                        self._stdio_stop_event is not None and not self._stdio_stop_event.is_set() and not rfile.closed
                    ):
                        if cast(io.BufferedReader, rfile).peek(1):
                            data = cast(io.BufferedReader, rfile).read1(10000)

                            self.loop.call_soon_threadsafe(protocol.data_received, data)

                with ThreadPoolExecutor(max_workers=1, thread_name_prefix="aio_readline") as stdio_executor:
                    await asyncio.wrap_future(stdio_executor.submit(run))

            self.loop.run_until_complete(aio_readline(transport.rfile, protocol))

        self._run_func = run_io_nonblocking

    @_logger.call
    async def start_tcp(self, host: Union[str, Sequence[str], None] = None, port: int = 0) -> None:
        self.mode = JsonRpcServerMode.TCP

        self._server = await self.loop.create_server(self.create_protocol, host, port, reuse_address=True)

        self._serve_func = self._server.serve_forever
        self._run_func = self.loop.run_forever

    @_logger.call
    def start_pipe(self, pipe_name: Optional[str]) -> None:
        from typing import TYPE_CHECKING

        if pipe_name is None:
            raise ValueError("pipe name missing.")

        self.mode = JsonRpcServerMode.PIPE

        try:
            #  check if we are on windows and using the ProactorEventLoop, to use the undocumented
            #  create_pipe_connection method
            if sys.platform == "win32" and hasattr(self.loop, "create_pipe_connection"):
                if TYPE_CHECKING:
                    from asyncio.streams import StreamReaderProtocol
                    from asyncio.windows_events import ProactorEventLoop

                self.loop.run_until_complete(
                    cast("ProactorEventLoop", self.loop).create_pipe_connection(
                        lambda: cast("StreamReaderProtocol", self.create_protocol()), pipe_name
                    ),
                )
            else:
                self.loop.run_until_complete(self.loop.create_unix_connection(self.create_protocol, pipe_name))
        except NotImplementedError:
            raise NotSupportedError("Pipe transport is not supported on this platform.")

        self._run_func = self.loop.run_forever

    @_logger.call
    def start_socket(self, port: int) -> None:
        self.mode = JsonRpcServerMode.SOCKET

        self.loop.run_until_complete(self.loop.create_connection(self.create_protocol, port=port))

        self._run_func = self.loop.run_forever

    @_logger.call
    def run(self) -> None:
        if self._run_func is None:
            self._logger.warning("server is not started.")
            return
        self._run_func()

    @_logger.call
    async def serve(self) -> None:
        if self._serve_func is None:
            self._logger.warning("server is not started.")
            return
        await self._serve_func()
