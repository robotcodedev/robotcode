import asyncio
from base64 import decode
import json
import logging
import re
import sys
from abc import ABC, abstractmethod
from asyncio.events import AbstractEventLoop, AbstractServer
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Type, Union, cast

from pydantic import BaseModel

from .logging_helpers import define_logger

__all__ = [
    "JsonRPCMessage",
    "JsonRPCNotification",
    "JsonRPCRequestMessage",
    "JsonRPCResponseMessage",
    "JsonRPCErrorMessage",
    "JsonRPCProtocol",
    "JsonRPCServer",
    "JsonRPCException",
    "JsonRPCParseError",
    "InvalidProtocolVersionException",
]


class JsonRPCErrors:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32000
    SERVER_ERROR_END = -32099


PROTOCOL_VERSION = "2.0"


class JsonRPCMessage(BaseModel):
    jsonrpc: str = PROTOCOL_VERSION


class JsonRPCNotification(JsonRPCMessage):
    method: str
    params: Optional[Any] = None


class JsonRPCRequestMessage(JsonRPCMessage):
    id: Union[str, int, None]
    method: str
    params: Optional[Any] = None


class JsonRPCResponseMessage(JsonRPCMessage):
    id: Union[str, int, None]
    result: Any


class JsonRPCErrorObject(BaseModel):
    code: int
    message: str
    data: Any = None


class JsonRPCErrorMessage(JsonRPCResponseMessage):
    """A class that represents json rpc response message."""

    error: Optional[JsonRPCErrorObject] = None


class JsonRPCException(Exception):
    pass


class JsonRPCParseError(JsonRPCException):
    pass


class InvalidProtocolVersionException(JsonRPCParseError):
    pass


def json_rpc_message_from_dict(data: Dict[Any, Any]):
    if "jsonrpc" in data:
        if data["jsonrpc"] != PROTOCOL_VERSION:
            raise InvalidProtocolVersionException("Invalid JSON-RPC2 protocol version.")

        if "id" in data:
            if "method" in data:
                return JsonRPCRequestMessage(**data)
            else:
                if "error" in data:
                    error = data.pop("error")
                    return JsonRPCErrorMessage(error=JsonRPCErrorObject(**error), **data)

                return JsonRPCResponseMessage(**data)
        else:
            return JsonRPCNotification(**data)
    return data


class JsonRPCProtocol(asyncio.Protocol):
    def __init__(self, server: Optional["JsonRPCServer"]):
        self.server = server
        self.transport: Optional[asyncio.Transport] = None
        self._message_buf = bytes()

    @define_logger
    def logger(self) -> logging.Logger:
        ...

    @define_logger(postfix=".data")
    def __message_logger(self) -> logging.Logger:
        ...

    @logger.call
    def connection_made(self, transport: asyncio.BaseTransport):
        self.transport = cast(asyncio.Transport, transport)

    CHARSET = "utf-8"
    CONTENT_TYPE = "application/vscode-jsonrpc"

    MESSAGE_PATTERN = re.compile(
        rb"(?:[^\r\n]*\r\n)*"
        + rb"(Content-Length: ?(?P<length>\d+)\r\n)"
        + rb"((Content-Type: ?(?P<content_type>[^\r\n;]+)"
        + rb"(; *(charset=(?P<charset>[^\r\n]+))?)?\r\n)|(?:[^\r\n]+\r\n))*"
        + rb"\r\n(?P<body>.*)",
        re.DOTALL,
    )

    def data_received(self, data: bytes):
        while len(data):
            # Append the incoming chunk to the message buffer
            self._message_buf += data

            # Look for the body of the message
            found = self.MESSAGE_PATTERN.match(self._message_buf)

            body = found.group("body") if found else b""
            length = int(found.group("length")) if found else 1

            charset = (
                found.group("charset").decode("ascii") if found and found.group("charset") is not None else self.CHARSET
            )

            if len(body) < length:
                return

            self.__message_logger.debug(
                lambda: "received with content:\n" + self._message_buf.decode(charset).replace("\r\n", "\n")
            )

            body, data = body[:length], body[length:]
            self._message_buf = bytes()
            message = None
            try:
                message = json_rpc_message_from_dict(json.loads(body.decode(charset)))
            except BaseException as e:
                self.send_error(JsonRPCErrors.PARSE_ERROR, str(e))

            self.handle_message(message)

    def eof_received(self):
        pass

    @logger.call
    def send_response(self, id: Optional[Union[str, int, None]], result: Optional[Any] = None):
        self.send_data(JsonRPCResponseMessage(id=id, result=result))

    @logger.call
    def send_error(
        self,
        code: int,
        message: str,
        id: Optional[Union[str, int, None]] = None,
        data: Optional[Any] = None,
    ):
        self.send_data(
            JsonRPCErrorMessage(
                id=id,
                result=None,
                error=JsonRPCErrorObject(code=code, message=message, data=data),
            )
        )

    @logger.call
    def send_data(self, message: JsonRPCMessage):
        body = message.json(by_alias=True, indent=True).encode(self.CHARSET)

        header = (
            f"Content-Length: {len(body)}\r\n" f"Content-Type: {self.CONTENT_TYPE}; charset={self.CHARSET}\r\n\r\n"
        ).encode("ascii")

        self.__message_logger.debug(
            lambda: "sending with content:\n"
            + (header.decode("ascii") + body.decode(self.CHARSET)).replace("\r\n", "\n")
        )

        if self.transport is not None:
            self.transport.write(header + body)

    @logger.call
    def handle_message(self, message: Union[JsonRPCMessage, List[JsonRPCMessage]]):
        if isinstance(message, list):
            for m in message:
                self.handle_message(m)
        elif isinstance(message, JsonRPCRequestMessage):
            self.handle_request(message)
        elif isinstance(message, JsonRPCNotification):
            self.handle_notification(message)
        elif isinstance(message, JsonRPCNotification):
            self.handle_notification(message)
        elif isinstance(message, JsonRPCResponseMessage):
            self.handle_respose(message)

    @logger.call
    def handle_request(self, message: JsonRPCRequestMessage):
        if self.server is not None:
            self.server.handle_request(message)

    @logger.call
    def handle_notification(self, message: JsonRPCNotification):
        if self.server is not None:
            self.server.handle_notification(message)

    @logger.call
    def handle_respose(self, message: JsonRPCResponseMessage):
        if self.server is not None:
            self.server.handle_respose(message)


class StdOutTransportAdapter(asyncio.Transport):
    def __init__(self, rfile: BinaryIO, wfile: BinaryIO):

        self.rfile = rfile
        self.wfile = wfile

    def close(self):
        self.rfile.close()
        self.wfile.close()

    def write(self, data: bytes):
        self.wfile.write(data)
        self.wfile.flush()


class JsonRPCServer(ABC):
    def __init__(
        self,
        protocol_cls: Type[JsonRPCProtocol] = JsonRPCProtocol,
        loop: Optional[AbstractEventLoop] = None,
        max_workers: Optional[int] = None,
    ):
        self._max_workers = max_workers
        self._run_func: Optional[Callable[[], None]] = None
        self._server: Optional[AbstractServer] = None

        self._stop_event = Event()

        self._thread_pool_executor: Optional[ThreadPoolExecutor] = None

        self.loop = loop or asyncio.get_event_loop()

        # self.loop.set_debug(True)

        try:
            asyncio.get_child_watcher().attach_loop(self.loop)
        except NotImplementedError:
            pass

        self.protocol = protocol_cls(self)

    @define_logger
    def logger(self) -> logging.Logger:
        ...

    @logger.call
    def shutdown(self):
        if self._stop_event is not None:
            self._stop_event.set()

        if self._thread_pool_executor:
            self._thread_pool_executor.shutdown()

        if self._server:
            self._server.close()
            self.loop.run_until_complete(self._server.wait_closed())

        self.loop.close()

    @logger.call
    def start_io(self, stdin: Optional[BinaryIO] = None, stdout: Optional[BinaryIO] = None):
        async def aio_readline(rfile: BinaryIO):
            """Reads data from stdin in separate thread (asynchronously)."""

            while not self._stop_event.is_set() and not rfile.closed:

                def read():
                    return rfile.read(1)

                self.protocol.data_received(await self.loop.run_in_executor(None, read))

        transport = StdOutTransportAdapter(stdin or sys.stdin.buffer, stdout or sys.stdout.buffer)
        self.protocol.connection_made(transport)

        def run_io():
            self.loop.run_until_complete(aio_readline(stdin or sys.stdin.buffer))

        self._run_func = run_io

    @logger.call
    def start_tcp(self, host: str, port: int):
        self._server = self.loop.run_until_complete(self.loop.create_server(lambda: self.protocol, host, port))

        self._run_func = self.loop.run_forever

    def run(self):
        if self._run_func is None:
            self.logger.warning("server is not started.")
            return
        self._run_func()

    @property
    def thread_pool_executor(self) -> ThreadPoolExecutor:
        """Returns thread pool instance (lazy initialization)."""
        if not self._thread_pool_executor:
            self._thread_pool_executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix=type(self).__qualname__,
            )

        return self._thread_pool_executor

    @abstractmethod
    def handle_request(self, message: JsonRPCRequestMessage):
        ...

    @abstractmethod
    def handle_notification(self, message: JsonRPCNotification):
        ...

    @abstractmethod
    def handle_respose(self, message: JsonRPCResponseMessage):
        ...

    def send_data(self, message: JsonRPCMessage):
        self.protocol.send_data(message)

    def send_error(
        self,
        code: int,
        message: str,
        id: Optional[Union[str, int, None]] = None,
        data: Optional[Any] = None,
    ):
        self.protocol.send_error(code, message, id, data)

    def send_response(self, id: Optional[Union[str, int, None]], result: Optional[Any] = None):
        self.protocol.send_response(id, result)
