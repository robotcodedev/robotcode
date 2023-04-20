import abc
import asyncio
import io
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from types import TracebackType
from typing import (
    BinaryIO,
    Callable,
    Coroutine,
    Generic,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
)

from robotcode.core.logging import LoggingDescriptor
from robotcode.core.types import ServerMode, TcpParams
from typing_extensions import Self

from .protocol import JsonRPCException

__all__ = ["JsonRPCServer"]

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


class JsonRPCServer(Generic[TProtocol], abc.ABC):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        mode: ServerMode = ServerMode.STDIO,
        tcp_params: TcpParams = TcpParams(None, 0),
        pipe_name: Optional[str] = None,
    ):
        self.mode = mode
        self.tcp_params = tcp_params
        self.pipe_name = pipe_name

        self._run_func: Optional[Callable[[], None]] = None
        self._serve_func: Optional[Callable[[], Coroutine[None, None, None]]] = None
        self._server: Optional[asyncio.AbstractServer] = None

        self._stdio_stop_event: Optional[threading.Event] = None

        self._in_closing = False
        self._closed = False

        self.loop = asyncio.get_event_loop()
        if self.loop is not None:
            self.loop.slow_callback_duration = 10

    def __del__(self) -> None:
        self.close()

    @_logger.call
    def start(self) -> None:
        if self.mode == ServerMode.STDIO:
            self.start_stdio()
        elif self.mode == ServerMode.TCP:
            self.loop.run_until_complete(self.start_tcp(self.tcp_params.host, self.tcp_params.port))
        elif self.mode == ServerMode.PIPE:
            self.start_pipe(self.pipe_name)
        elif self.mode == ServerMode.PIPE_SERVER:
            self.loop.run_until_complete(self.start_pipe_server(self.pipe_name))
        elif self.mode == ServerMode.SOCKET:
            self.start_socket(
                self.tcp_params.port,
                self.tcp_params.host
                if isinstance(self.tcp_params.host, str)
                else self.tcp_params.host[0]
                if self.tcp_params.host
                else None,
            )
        else:
            raise JsonRPCException(f"Unknown server mode {self.mode}")

    @_logger.call
    async def start_async(self) -> None:
        if self.mode == ServerMode.TCP:
            await self.start_tcp(self.tcp_params.host, self.tcp_params.port)
        else:
            raise JsonRPCException(f"Unsupported server mode {self.mode}")

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

    async def __aenter__(self) -> Self:
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

    def __enter__(self) -> Self:
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
        self.mode = ServerMode.STDIO

        transport = StdOutTransportAdapter(sys.__stdin__.buffer, sys.__stdout__.buffer)

        protocol = self.create_protocol()

        def run_io_nonblocking() -> None:
            stop_event = self._stdio_stop_event = threading.Event()

            async def aio_readline(rfile: BinaryIO, protocol: asyncio.Protocol) -> None:
                protocol.connection_made(transport)

                def run() -> None:
                    while not stop_event.is_set() and not rfile.closed:
                        if cast(io.BufferedReader, rfile).peek(1):
                            data = cast(io.BufferedReader, rfile).read1(10000)

                            self.loop.call_soon_threadsafe(protocol.data_received, data)
                        else:
                            # no data available, wait a bit if we are not closing
                            stop_event.wait(0.01)

                with ThreadPoolExecutor(max_workers=1, thread_name_prefix="aio_readline") as stdio_executor:
                    self._stdio_threadpool = stdio_executor
                    await asyncio.wrap_future(stdio_executor.submit(run))

            self.loop.run_until_complete(aio_readline(transport.rfile, protocol))

        self._run_func = run_io_nonblocking

    @_logger.call
    async def start_tcp(self, host: Union[str, Sequence[str], None] = None, port: int = 0) -> None:
        self.mode = ServerMode.TCP

        self._server = await self.loop.create_server(self.create_protocol, host, port, reuse_address=True)

        self._serve_func = self._server.serve_forever
        self._run_func = self.loop.run_forever

    @_logger.call
    def start_pipe(self, pipe_name: Optional[str]) -> None:
        from typing import TYPE_CHECKING

        if pipe_name is None:
            raise ValueError("pipe name missing.")

        self.mode = ServerMode.PIPE

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
        except NotImplementedError as e:
            raise NotSupportedError("Pipe transport is not supported on this platform.") from e

        self._run_func = self.loop.run_forever

    @_logger.call
    async def start_pipe_server(self, pipe_name: Optional[str]) -> None:
        from typing import TYPE_CHECKING

        if pipe_name is None:
            raise ValueError("pipe name missing.")

        self.mode = ServerMode.PIPE_SERVER

        try:
            #  check if we are on windows and using the ProactorEventLoop, to use the undocumented
            #  create_pipe_connection method
            if sys.platform == "win32" and hasattr(self.loop, "start_serving_pipe"):
                if TYPE_CHECKING:
                    from asyncio.streams import StreamReaderProtocol
                    from asyncio.windows_events import ProactorEventLoop

                await cast("ProactorEventLoop", self.loop).start_serving_pipe(
                    lambda: cast("StreamReaderProtocol", self.create_protocol()), pipe_name
                )

            else:
                self._server = await self.loop.create_unix_server(self.create_protocol, pipe_name)
        except NotImplementedError as e:
            raise NotSupportedError("Pipe transport is not supported on this platform.") from e
        if self._server is not None:
            self._serve_func = self._server.serve_forever
        self._run_func = self.loop.run_forever

    @_logger.call
    def start_socket(self, port: int, host: Optional[str] = None) -> None:
        self.mode = ServerMode.SOCKET

        self.loop.run_until_complete(
            self.loop.create_connection(self.create_protocol, port=port)
            if host is None
            else self.loop.create_connection(self.create_protocol, host=host, port=port)
        )

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
