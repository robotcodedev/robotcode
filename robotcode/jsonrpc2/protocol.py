from __future__ import annotations

import asyncio
import inspect
import json
import re
import threading
import weakref
from asyncio.exceptions import CancelledError
from collections import OrderedDict
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

from pydantic import BaseModel, Field
from pydantic.typing import get_args, get_origin

from ..utils.async_event import async_event
from ..utils.inspect import ensure_coroutine, iter_methods
from ..utils.logging import LoggingDescriptor

if TYPE_CHECKING:
    from .server import JsonRPCServer

__all__ = [
    "JsonRPCErrors",
    "JsonRPCMessage",
    "JsonRPCNotification",
    "JsonRPCRequest",
    "JsonRPCResponse",
    "JsonRPCError",
    "JsonRPCErrorObject",
    "JsonRPCProtocol",
    "JsonRPCException",
    "JsonRPCParseError",
    "InvalidProtocolVersionException",
    "rpc_method",
    "RpcRegistry",
    "JsonRPCProtocolPart",
    "ProtocolPartDescriptor",
    "GenericJsonRPCProtocolPart",
    "TProtocol",
]

T = TypeVar("T")
TResult = TypeVar("TResult", bound=Any)


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


class JsonRPCRequest(JsonRPCMessage):
    id: Union[int, str, None] = Field(...)
    method: str = Field(...)
    params: Optional[Any] = None


class JsonRPCResponse(JsonRPCMessage):
    id: Union[int, str, None] = Field(...)
    result: Any = Field(...)


class JsonRPCErrorObject(BaseModel):
    code: int = Field(...)
    message: Optional[str]
    data: Optional[Any] = None


class JsonRPCError(JsonRPCResponse):
    """A class that represents json rpc response message."""

    error: JsonRPCErrorObject = Field(...)
    result: Optional[Any] = None


class JsonRPCException(Exception):
    pass


class JsonRPCErrorException(JsonRPCException):
    def __init__(self, code: int, message: str, data: Optional[Any] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class JsonRPCParseError(JsonRPCException):
    pass


class InvalidProtocolVersionException(JsonRPCParseError):
    pass


class RpcMethodEntry(NamedTuple):
    name: str
    method: Callable[..., Any]
    param_type: Optional[Type[Any]]


@runtime_checkable
class RpcMethod(Protocol):
    __rpc_method__: RpcMethodEntry


_F = TypeVar("_F", bound=Callable[..., Any])


@overload
def rpc_method(_func: _F) -> _F:
    ...


@overload
def rpc_method(*, name: Optional[str] = None, param_type: Optional[Type[Any]] = None) -> Callable[[_F], _F]:
    ...


def rpc_method(
    _func: Optional[_F] = None, *, name: Optional[str] = None, param_type: Optional[Type[Any]] = None
) -> Callable[[_F], _F]:
    def _decorator(func: _F) -> Callable[[_F], _F]:

        if inspect.isclass(_func):
            raise Exception(f"Not supported type {type(func)}.")

        if isinstance(func, classmethod):
            f = cast(classmethod, func).__func__
        elif isinstance(func, staticmethod):
            f = cast(staticmethod, func).__func__
        else:
            f = func

        real_name = name if name is not None else f.__name__ if f is not None else None
        if real_name is None or not real_name:
            raise Exception("name is empty.")

        cast(RpcMethod, f).__rpc_method__ = RpcMethodEntry(real_name, f, param_type)
        return func

    if _func is None:
        return cast(Callable[[_F], _F], _decorator)
    return _decorator(_func)


@runtime_checkable
class HasRpcRegistry(Protocol):
    __rpc_registry__: RpcRegistry


class RpcRegistry:
    _class_registries: Dict[Type[Any], RpcRegistry] = {}

    def __init__(self, owner: Any = None, parent: Optional[RpcRegistry] = None):
        self.__owner = owner
        self.__methods: Dict[str, RpcMethodEntry] = {}
        self.__initialized = False
        self.__class_parts: Dict[str, Type[Any]] = {}
        self.__class_part_instances: weakref.WeakSet[GenericJsonRPCProtocolPart[Any]] = weakref.WeakSet()

    def __set_name__(self, owner: Any, name: str) -> None:
        self.__owner = owner

    def __get__(self, obj: Any, objtype: Type[Any]) -> "RpcRegistry":
        if obj is None and objtype == self.__owner:
            return self

        if obj is not None:
            if not isinstance(obj, HasRpcRegistry):
                cast(HasRpcRegistry, obj).__rpc_registry__ = RpcRegistry(obj)

            return cast(HasRpcRegistry, obj).__rpc_registry__

        if objtype not in RpcRegistry._class_registries:
            RpcRegistry._class_registries[objtype] = RpcRegistry(objtype)

        return RpcRegistry._class_registries[objtype]

    def _reset(self) -> None:
        self.__methods.clear()
        self.__initialized = False

    def add_class_part(self, name: str, class_type: Type[Any]) -> None:
        self._reset()
        self.__class_parts[name] = class_type

    def add_class_part_instance(self, instance: GenericJsonRPCProtocolPart[Any]) -> None:
        self._reset()
        self.__class_part_instances.add(instance)

    @property
    def parts(self) -> Set[GenericJsonRPCProtocolPart[Any]]:
        self.__ensure_initialized()

        return set(self.__class_part_instances)

    def __ensure_initialized(self) -> None:
        def get_methods(obj: Any) -> Dict[str, RpcMethodEntry]:
            return {
                r.__rpc_method__.name: RpcMethodEntry(
                    r.__rpc_method__.name,
                    m,
                    r.__rpc_method__.param_type,
                )
                for m, r in map(
                    lambda m: (m, cast(RpcMethod, m)), filter(lambda m: isinstance(m, RpcMethod), iter_methods(obj))
                )
            }

        if not self.__initialized:

            if inspect.isclass(self.__owner):
                self.__methods = get_methods(self.__owner)

                for cp in self.__class_parts.items():
                    self.__methods.update(get_methods(cp))
            else:
                registries: List[RpcRegistry] = []
                for m in inspect.getmro(type(self.__owner)):
                    r = self._class_registries.get(m, None)
                    if r is not None:
                        registries.insert(0, r)
                for r in registries:
                    for k in r.__class_parts.keys():
                        getattr(self.__owner, k)

                self.__methods = get_methods(self.__owner)

                for cpi in self.__class_part_instances:
                    self.__methods.update(get_methods(cpi))

        self.__initialized = True

    def initialize_parts(self) -> None:
        self.__ensure_initialized()

    @property
    def methods(self) -> Dict[str, RpcMethodEntry]:
        self.__ensure_initialized()

        return self.__methods

    def add_method(self, name: str, func: Callable[..., Any], param_type: Optional[Type[Any]] = None) -> None:
        self.__ensure_initialized()

        self.__methods[name] = RpcMethodEntry(name, func, param_type)

    def remove_method(self, name: str) -> Optional[RpcMethodEntry]:
        self.__ensure_initialized()
        return self.__methods.pop(name, None)

    def get_entry(self, name: str) -> Optional[RpcMethodEntry]:
        self.__ensure_initialized()
        return self.__methods.get(name, None)

    def get_method(self, name: str) -> Optional[Callable[..., Any]]:
        result = self.get_entry(name)
        if result is None:
            return None
        return result.method

    def get_param_type(self, name: str) -> Optional[Type[Any]]:
        result = self.get_entry(name)
        if result is None:
            return None
        return result.param_type


def _json_rpc_message_from_dict(
    data: Union[Dict[Any, Any], List[Dict[Any, Any]]]
) -> Generator[JsonRPCMessage, None, None]:
    def inner(d: Dict[Any, Any]) -> JsonRPCMessage:
        if "jsonrpc" in d:
            if d["jsonrpc"] != PROTOCOL_VERSION:
                raise InvalidProtocolVersionException("Invalid JSON-RPC2 protocol version.")

            if "id" in d:
                if "method" in d:
                    return JsonRPCRequest(**d)
                else:
                    if "error" in d:
                        error = d.pop("error")
                        return JsonRPCError(error=JsonRPCErrorObject(**error), **d)

                    return JsonRPCResponse(**d)
            else:
                return JsonRPCNotification(**d)
        raise JsonRPCException("Invalid JSON-RPC2 Message")

    if isinstance(data, list):
        for e in data:
            yield inner(e)
    else:
        yield inner(data)


class _SendedRequestEntry(NamedTuple):
    future: asyncio.Future[Any]
    result_type: Union[Type[Any], Callable[[Any], Any], None]


def _try_convert_value(value: Any, value_type_or_converter: Union[Type[Any], Callable[[Any], Any], None]) -> Any:
    if value_type_or_converter is None or value_type_or_converter == Any:
        return value
    if isinstance(value_type_or_converter, type):
        if isinstance(value, value_type_or_converter):
            return value

        if issubclass(value_type_or_converter, BaseModel):
            return value_type_or_converter.parse_obj(value)
    elif get_origin(cast(Type[Any], value_type_or_converter)) == list and isinstance(value, List):
        p = get_args(cast(Type[Any], value_type_or_converter))
        if len(p) > 0:
            return [_try_convert_value(e, p[0]) for e in value]
        else:
            return value
    elif get_origin(cast(Type[Any], value_type_or_converter)) == dict and isinstance(value, dict):
        p = get_args(cast(Type[Any], value_type_or_converter))
        if len(p) > 1:
            return {_try_convert_value(k, p[0]): _try_convert_value(v, p[1]) for k, v in value.items()}
        else:
            return value
    elif get_origin(cast(Type[Any], value_type_or_converter)) is not None:
        return get_origin(cast(Type[Any], value_type_or_converter))(value)
    elif callable(value_type_or_converter):
        return value_type_or_converter(value)

    return value


def _convert_params(
    callable: Callable[..., Any], param_type: Optional[Type[Any]], params: Any
) -> Tuple[List[Any], Dict[str, Any]]:
    if params is None:
        return ([], {})
    if param_type is None:
        if isinstance(params, Mapping):
            return ([], dict(**params))
        else:
            return ([params], {})

    # try to convert the dict to correct type
    if issubclass(param_type, BaseModel):
        converted_params = param_type.parse_obj(params)
    else:
        converted_params = param_type(**params)

    signature = inspect.signature(callable)

    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())

    kw_args = {}
    args = []
    params_added = False
    rest = list(converted_params.__dict__.keys())
    for v in signature.parameters.values():
        if v.name in converted_params.__dict__:
            if v.kind == inspect.Parameter.POSITIONAL_ONLY:
                args.append(getattr(converted_params, v.name))
            else:
                kw_args[v.name] = getattr(converted_params, v.name)
            rest.remove(v.name)
        elif v.name == "params":
            if v.kind == inspect.Parameter.POSITIONAL_ONLY:
                args.append(converted_params)
                params_added = True
            else:
                kw_args[v.name] = converted_params
                params_added = True
    if has_var_kw:
        for r in rest:
            kw_args[r] = getattr(converted_params, r)
        if not params_added:
            kw_args["params"] = converted_params
    return (args, kw_args)


class JsonRPCProtocol(asyncio.Protocol):

    _logger = LoggingDescriptor()
    _message_logger = LoggingDescriptor(postfix=".message")
    registry = RpcRegistry()

    def __init__(self, server: "JsonRPCServer[Any]"):
        self.server = server
        self.read_transport: Optional[asyncio.ReadTransport] = None
        self.write_transport: Optional[asyncio.WriteTransport] = None
        self._sended_request_lock = threading.RLock()
        self._sended_request: OrderedDict[Union[str, int], _SendedRequestEntry] = OrderedDict()
        self._sended_request_count = 0
        self._received_request_lock = threading.RLock()
        self._received_request: OrderedDict[Union[str, int, None], asyncio.Future[Any]] = OrderedDict()
        self._message_buf = bytes()

    @async_event
    async def on_connection_made(sender, transport: asyncio.BaseTransport) -> None:
        ...

    @async_event
    async def on_connection_lost(sender, exc: Optional[BaseException]) -> None:
        ...

    @_logger.call
    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        super().connection_made(transport)
        if isinstance(transport, asyncio.ReadTransport):
            self.read_transport = transport
        if isinstance(transport, asyncio.WriteTransport):
            self.write_transport = transport

        asyncio.ensure_future(self.on_connection_made(self, transport))

    @_logger.call
    def connection_lost(self, exc: Optional[BaseException]) -> None:
        asyncio.ensure_future(self.on_connection_lost(self, exc))

    @_logger.call
    def eof_received(self) -> Optional[bool]:
        return False

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

    def data_received(self, data: bytes) -> None:
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
            try:
                self._handle_messages_generator(_json_rpc_message_from_dict(json.loads(body.decode(charset))))
            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self._logger.exception(e)
                self.send_error(JsonRPCErrors.PARSE_ERROR, str(e))

    def _handle_messages_generator(self, generator: Generator[JsonRPCMessage, None, None]) -> None:
        def done(f: asyncio.Future[Any]) -> None:
            ex = f.exception()
            if ex is not None and not isinstance(ex, CancelledError):
                self._logger.exception(ex, exc_info=ex)

        for m in generator:
            future = asyncio.ensure_future(
                self.handle_message(m), loop=self.server.loop if self.server is not None else None
            )
            future.add_done_callback(done)

    @_logger.call
    async def handle_message(self, message: JsonRPCMessage) -> None:
        if isinstance(message, JsonRPCRequest):
            await self.handle_request(message)
        elif isinstance(message, JsonRPCNotification):
            await self.handle_notification(message)
        elif isinstance(message, JsonRPCError):
            await self.handle_error(message)
        elif isinstance(message, JsonRPCResponse):
            await self.handle_response(message)

    @_logger.call
    def send_response(self, id: Optional[Union[str, int, None]], result: Optional[Any] = None) -> None:
        self.send_message(JsonRPCResponse(id=id, result=result))

    @_logger.call
    def send_error(
        self,
        code: int,
        message: str,
        id: Optional[Union[str, int, None]] = None,
        data: Optional[Any] = None,
    ) -> None:
        error_obj = JsonRPCErrorObject(code=code, message=message)
        if data is not None:
            error_obj.data = data

        self.send_message(
            JsonRPCError(
                id=id,
                error=error_obj,
            )
        )

    @_logger.call
    def send_message(self, message: JsonRPCMessage) -> None:
        message.jsonrpc = PROTOCOL_VERSION

        body = message.json(by_alias=True, indent=False, exclude_unset=True, exclude_defaults=True).encode(self.CHARSET)

        header = (
            f"Content-Length: {len(body)}\r\n" f"Content-Type: {self.CONTENT_TYPE}; charset={self.CHARSET}\r\n\r\n"
        ).encode("ascii")

        self._message_logger.debug(
            lambda: "write ->\n" + (header.decode("ascii") + body.decode(self.CHARSET)).replace("\r\n", "\n")
        )

        if self.write_transport is not None:
            self.write_transport.write(header + body)

    def send_request(
        self,
        method: str,
        params: Optional[Any] = None,
        return_type_or_converter: Union[Type[TResult], Callable[[Any], TResult], None] = None,
    ) -> asyncio.Future[TResult]:

        result: asyncio.Future[TResult] = asyncio.get_event_loop().create_future()

        with self._sended_request_lock:
            self._sended_request_count += 1
            id = self._sended_request_count

            self._sended_request[id] = _SendedRequestEntry(result, return_type_or_converter)

        self.send_message(JsonRPCRequest(id=id, method=method, params=params))

        return result

    async def send_request_async(
        self,
        method: str,
        params: Optional[Any] = None,
        return_type: Union[Type[TResult], Callable[[Any], TResult], None] = None,
    ) -> TResult:
        return await self.send_request(method, params, return_type)

    def send_notification(self, method: str, params: Any) -> None:
        self.send_message(JsonRPCNotification(method=method, params=params))

    @_logger.call(exception=True)
    async def handle_response(self, message: JsonRPCResponse) -> None:
        if message.id is None:
            error = "Invalid response. Response id is null"
            self._logger.warning(error)
            self.send_error(JsonRPCErrors.INTERNAL_ERROR, error)
            return

        with self._sended_request_lock:
            entry = self._sended_request.pop(message.id, None)

        if entry is None:
            error = f"Invalid response. Could not find id '{message.id}' in our request list"
            self._logger.warning(error)
            self.send_error(JsonRPCErrors.INTERNAL_ERROR, error)
            return

        try:
            entry.future.set_result(_try_convert_value(message.result, entry.result_type))
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            entry.future.set_exception(e)

    @_logger.call
    async def handle_error(self, message: JsonRPCError) -> None:
        raise NotImplementedError()

    async def handle_request(self, message: JsonRPCRequest) -> None:
        e = self.registry.get_entry(message.method)

        if e is None or not callable(e.method):
            self.send_error(
                JsonRPCErrors.METHOD_NOT_FOUND,
                f"Unknown method: {message.method}",
                id=message.id,
            )
            return

        try:
            params = _convert_params(e.method, e.param_type, message.params)

            result = asyncio.ensure_future(ensure_coroutine(e.method)(*params[0], **params[1]))

            with self._received_request_lock:
                self._received_request[message.id] = result

            try:
                self.send_response(message.id, await result)
            finally:
                with self._received_request_lock:
                    self._received_request.pop(message.id, None)

        except asyncio.CancelledError:
            self._logger.info(f"request message {repr(message)} canceled")
        except (SystemExit, KeyboardInterrupt):
            raise
        except JsonRPCErrorException as ex:
            self._logger.exception(ex)
            self.send_error(ex.code, ex.message, id=message.id, data=ex.data)
        except BaseException as e:
            self._logger.exception(e)
            self.send_error(JsonRPCErrors.INTERNAL_ERROR, str(e), id=message.id)

    async def cancel_received_request(self, id: Union[int, str, None]) -> None:
        with self._received_request_lock:
            future = self._received_request.get(id, None)
        if future is not None and not future.cancelled():
            future.cancel()

    async def handle_notification(self, message: JsonRPCNotification) -> None:
        e = self.registry.get_entry(message.method)

        if e is None or not callable(e.method):
            self._logger.warning(f"Unknown method: {message.method}")
            # self.send_error(JsonRPCErrors.METHOD_NOT_FOUND, f"Unknown method: {message.method}")
            return
        try:
            params = _convert_params(e.method, e.param_type, message.params)
            result = e.method(*params[0], **params[1])
            if inspect.isawaitable(result):
                await result
        except CancelledError:
            pass
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._logger.exception(e)


TProtocol = TypeVar("TProtocol", bound=(JsonRPCProtocol))


class GenericJsonRPCProtocolPart(Generic[TProtocol]):
    def __init__(self, parent: TProtocol) -> None:
        super().__init__()
        self._parent = weakref.ref(parent)
        parent.registry.add_class_part_instance(self)

    @property
    def parent(self) -> TProtocol:
        result = self._parent()
        if result is None:
            raise JsonRPCException("WeakRef is not alive")
        return result


class JsonRPCProtocolPart(GenericJsonRPCProtocolPart[JsonRPCProtocol]):
    pass


TProtocolPart = TypeVar("TProtocolPart", bound=GenericJsonRPCProtocolPart[Any])


@runtime_checkable
class HasPartInstance(Protocol[TProtocolPart]):
    __rpc_part_instances__: Dict[Type[TProtocolPart], TProtocolPart]


class ProtocolPartDescriptor(Generic[TProtocolPart]):
    def __init__(self, instance_type: Type[TProtocolPart], *args: Any, **kwargs: Any):
        self._instance_type = instance_type
        self._instance_args = args
        self._instance_kwargs = kwargs

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        if not issubclass(owner, JsonRPCProtocol):
            raise AttributeError()
        owner.registry.add_class_part(name, self._instance_type)

    def __get__(self, obj: Optional[Any], objtype: Type[Any]) -> TProtocolPart:
        if obj is not None:
            if not isinstance(obj, HasPartInstance):
                cast(HasPartInstance[TProtocolPart], obj).__rpc_part_instances__ = {}

            if self._instance_type not in cast(HasPartInstance[TProtocolPart], obj).__rpc_part_instances__:
                instance = self._instance_type(*(obj, *self._instance_args), **self._instance_kwargs)
                cast(HasPartInstance[TProtocolPart], obj).__rpc_part_instances__[self._instance_type] = instance

                cast(JsonRPCProtocol, obj).registry.add_class_part_instance(instance)

            return cast(HasPartInstance[TProtocolPart], obj).__rpc_part_instances__[self._instance_type]

        return self._instance_type  # type: ignore
