import asyncio
import inspect
import json
import re
import sys
from abc import ABC
from asyncio.events import AbstractEventLoop, AbstractServer
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

from pydantic import BaseModel, Field

from .logging_helpers import LoggerInstance

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
    jsonrpc: str = Field(PROTOCOL_VERSION, const=True)


class JsonRPCNotification(JsonRPCMessage):
    method: str = Field(...)
    params: Optional[Any] = None


class JsonRPCRequestMessage(JsonRPCMessage):
    id: Union[str, int, None] = Field(...)
    method: str = Field(...)
    params: Optional[Any] = None


class JsonRPCResponseMessage(JsonRPCMessage):
    id: Union[str, int, None] = Field(...)
    result: Any = Field(...)


class JsonRPCErrorObject(BaseModel):
    code: int = Field(...)
    message: Optional[str]
    data: Optional[Any] = None


class JsonRPCErrorMessage(JsonRPCResponseMessage):
    """A class that represents json rpc response message."""

    error: JsonRPCErrorObject = Field(...)
    result: Optional[Any]


class JsonRPCException(Exception):
    pass


class JsonRPCParseError(JsonRPCException):
    pass


class InvalidProtocolVersionException(JsonRPCParseError):
    pass


def json_rpc_message_from_dict(data: Dict[Any, Any]) -> JsonRPCMessage:
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
    raise JsonRPCException("Invalid JSON-RPC2 Message")


class JsonRPCProtocol(asyncio.Protocol):
    _logger = LoggerInstance()
    _message_logger = LoggerInstance(postfix=".message")

    def __init__(self, server: Optional["JsonRPCServer"]):
        self.server = server
        self.transport: Optional[asyncio.Transport] = None
        self._message_buf = bytes()

    @_logger.call
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

            self._message_logger.debug(
                lambda: "received ->\n" + self._message_buf.decode(charset).replace("\r\n", "\n")
            )

            body, data = body[:length], body[length:]
            self._message_buf = bytes()
            message = None
            try:
                message = json_rpc_message_from_dict(json.loads(body.decode(charset)))
            except BaseException as e:
                self.send_error(JsonRPCErrors.PARSE_ERROR, str(e))
                return

            self.handle_message(message)

    def eof_received(self):
        pass

    @_logger.call
    def send_response(self, id: Optional[Union[str, int, None]], result: Optional[Any] = None):
        self.send_data(JsonRPCResponseMessage(id=id, result=result))

    @_logger.call
    def send_error(
        self,
        code: int,
        message: str,
        id: Optional[Union[str, int, None]] = None,
        data: Optional[Any] = None,
    ):
        error_obj = JsonRPCErrorObject(code=code, message=message)
        if data is not None:
            error_obj.data = data

        self.send_data(
            JsonRPCErrorMessage(
                id=id,
                error=error_obj,
            )
        )

    @_logger.call
    def send_data(self, message: JsonRPCMessage):
        message.jsonrpc = PROTOCOL_VERSION

        body = message.json(by_alias=True, indent=True, exclude_unset=True).encode(self.CHARSET)

        header = (
            f"Content-Length: {len(body)}\r\n" f"Content-Type: {self.CONTENT_TYPE}; charset={self.CHARSET}\r\n\r\n"
        ).encode("ascii")

        self._message_logger.debug(
            lambda: "write ->\n" + (header.decode("ascii") + body.decode(self.CHARSET)).replace("\r\n", "\n")
        )

        if self.transport is not None:
            self.transport.write(header + body)

    @_logger.call
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

    @_logger.call
    def handle_request(self, message: JsonRPCRequestMessage):
        if self.server is not None:
            self.server.handle_request(message)

    @_logger.call
    def handle_notification(self, message: JsonRPCNotification):
        if self.server is not None:
            self.server.handle_notification(message)

    @_logger.call
    def handle_respose(self, message: JsonRPCResponseMessage):
        if self.server is not None:
            self.server.handle_respose(message)


class RpcMethodEntry(NamedTuple):
    method: Callable[..., Any]
    param_type: Type


@runtime_checkable
class RpcMethod(Protocol):
    __rpc_method__: RpcMethodEntry


F = TypeVar("F", bound=Callable[..., Any])


@overload
def rpc_method(func: Callable[..., Any]) -> Callable[[F], F]:
    ...


@overload
def rpc_method(*, name: str = None, param_type: Type = object) -> Callable[[F], F]:
    ...


def rpc_method(func: Callable[..., Any] = None, *, name: str = None, param_type: Type = object) -> Callable[[F], F]:
    def _decorator(_func: Callable[..., Any]):

        if inspect.isclass(func):
            raise Exception(f"Not supported type {type(_func)}.")

        if isinstance(_func, classmethod):
            f = cast(classmethod, _func).__func__
        elif isinstance(_func, staticmethod):
            f = cast(staticmethod, _func).__func__
        else:
            f = _func

        real_name = name if name is not None else f.__name__ if f is not None else None
        if real_name is None or not real_name:
            raise Exception("name is empty.")

        cast(RpcMethod, f).__rpc_method__ = RpcMethodEntry(f, param_type)

        return _func

    if func is None:
        return _decorator
    return cast(Callable[[F], F], _decorator(func))


class RpcRegistry:
    __owner: Any = None
    __owner_name: str = ""

    def __init__(self, owner: Any = None, parent: "RpcRegistry" = None):
        self.__initialized = False
        self.__owner = owner
        self.__parent = parent
        self.__methods: Dict[str, RpcMethodEntry] = {}
        self.__childs: Dict[Tuple[Any, Type], RpcRegistry] = {}

    def __set_name__(self, owner: Any, name: str):
        self.__owner = owner
        self.__owner_name = name

    def __get__(self, obj: Any, objtype: Type) -> "RpcRegistry":
        if obj is None and objtype == self.__owner:
            return self

        if (obj, objtype) not in self.__childs:
            self.__childs[(obj, objtype)] = RpcRegistry(obj, self)

        return self.__childs[(obj, objtype)]

    def __ensure_initialized(self):
        if not self.__initialized:
            self.__methods = {
                k: RpcMethodEntry(
                    getattr(self.__owner, k), cast(RpcMethod, getattr(self.__owner, k)).__rpc_method__.param_type
                )
                for k in dir(self.__owner)
                if isinstance(getattr(self.__owner, k), RpcMethod)
            }
        self.__initialized = True

    @property
    def methods(self) -> Dict[str, RpcMethodEntry]:
        self.__ensure_initialized()

        if self.__parent is not None:
            return {**self.__parent.__methods, **self.__methods}

        return self.__methods

    def add_method(self, name: str, func: Callable[..., Any], param_type: Type = object):
        self.__ensure_initialized()

        self.__methods[name] = RpcMethodEntry(func, param_type)

    def remove_method(self, name: str):
        self.__ensure_initialized()
        return self.__methods.pop(name, None)

    def get_entry(self, name: str):
        self.__ensure_initialized()
        return self.__methods.get(name, None)

    def get_method(self, name: str):
        result = self.get_entry(name)
        if result is None:
            return None
        return result.method

    def get_param_type(self, name: str):
        result = self.get_entry(name)
        if result is None:
            return None
        return result.param_type


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

        self._loop = loop or asyncio.get_event_loop()

        # self.loop.set_debug(True)

        try:
            asyncio.get_child_watcher().attach_loop(self._loop)
        except NotImplementedError:
            pass

        self._protocol = protocol_cls(self)

    _logger = LoggerInstance()
    registry = RpcRegistry()

    @_logger.call
    def shutdown(self):
        if self._stop_event is not None:
            self._stop_event.set()

        if self._thread_pool_executor:
            self._thread_pool_executor.shutdown()

        if self._server:
            self._server.close()
            self._loop.run_until_complete(self._server.wait_closed())

        self._loop.close()

    @_logger.call
    def start_io(self, stdin: Optional[BinaryIO] = None, stdout: Optional[BinaryIO] = None):
        async def aio_readline(rfile: BinaryIO):
            """Reads data from stdin in separate thread (asynchronously)."""

            while not self._stop_event.is_set() and not rfile.closed:

                def read():
                    return rfile.read(1)

                self._protocol.data_received(await self._loop.run_in_executor(None, read))

        transport = StdOutTransportAdapter(stdin or sys.stdin.buffer, stdout or sys.stdout.buffer)
        self._protocol.connection_made(transport)

        def run_io():
            self._loop.run_until_complete(aio_readline(stdin or sys.stdin.buffer))

        self._run_func = run_io

    @_logger.call
    def start_tcp(self, host: str, port: int):
        self._server = self._loop.run_until_complete(self._loop.create_server(lambda: self._protocol, host, port))

        self._run_func = self._loop.run_forever

    def run(self):
        if self._run_func is None:
            self._logger.warning("server is not started.")
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

    def send_data(self, message: JsonRPCMessage):
        self._protocol.send_data(message)

    def send_error(
        self,
        code: int,
        message: str,
        id: Optional[Union[str, int, None]] = None,
        data: Optional[Any] = None,
    ):
        self._protocol.send_error(code, message, id, data)

    def send_response(self, id: Optional[Union[str, int, None]], result: Optional[Any] = None):
        self._protocol.send_response(id, result)

    def _convert_params(
        self, callable: Callable[..., Any], param_type: Type, params: Any
    ) -> Tuple[List, Dict[str, Any]]:
        if params is None:
            return ([], {})
        if param_type == object:
            if isinstance(params, Mapping):
                return ([], dict(**params))

        # try to convert the dict to correct type
        converted = param_type(**(params or {}))

        signature = inspect.signature(callable)

        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())

        kw_args = {}
        args = []
        params_added = False
        rest = list(converted.__dict__.keys())
        for v in signature.parameters.values():
            if v.name in converted.__dict__:
                if v.kind == inspect.Parameter.POSITIONAL_ONLY:
                    args.append(getattr(converted, v.name))
                elif has_var_kw:
                    kw_args[v.name] = getattr(converted, v.name)
                rest.remove(v.name)
            elif v.name == "params":
                if v.kind == inspect.Parameter.POSITIONAL_ONLY:
                    args.append(converted)
                    params_added = True
        if has_var_kw:
            for r in rest:
                kw_args[r] = getattr(converted, r)
            if not params_added:
                kw_args["params"] = converted
        return (args, kw_args)

    def handle_request(self, message: JsonRPCRequestMessage):
        e = self.registry.get_entry(message.method)

        if e is None or not callable(e.method):
            self.send_error(
                JsonRPCErrors.METHOD_NOT_FOUND,
                f"Unknown method: {message.method}",
                id=message.id,
            )
            return

        try:
            params = self._convert_params(e.method, e.param_type, message.params)
            self.send_response(message.id, e.method(*params[0], **params[1]))
        except BaseException as e:
            self.send_error(JsonRPCErrors.INTERNAL_ERROR, str(e), id=message.id)

    def handle_notification(self, message: JsonRPCNotification):
        e = self.registry.get_entry(message.method)

        if e is None or not callable(e.method):
            self.send_error(JsonRPCErrors.METHOD_NOT_FOUND, f"Unknown method: {message.method}")
            return

        try:
            params = self._convert_params(e.method, e.param_type, message.params)
            e.method(*params[0], **params[1])
        except BaseException as e:
            self.send_error(JsonRPCErrors.INTERNAL_ERROR, str(e), id=None)

    def handle_respose(self, message: JsonRPCResponseMessage):
        pass
