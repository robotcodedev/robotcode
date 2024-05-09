import asyncio
import inspect
import json
import threading
import traceback
from collections import OrderedDict
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from robotcode.core.concurrent import Task
from robotcode.core.utils.dataclasses import as_dict, as_json, from_dict
from robotcode.core.utils.inspect import ensure_coroutine
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import (
    JsonRPCException,
    JsonRPCProtocolBase,
    SendedRequestEntry,
)

from .dap_types import (
    ErrorBody,
    ErrorResponse,
    Event,
    Message,
    ProtocolMessage,
    Request,
    Response,
)


class DebugAdapterErrorResponseError(JsonRPCException):
    def __init__(self, error: ErrorResponse) -> None:
        super().__init__(
            f'{error.message} (seq={error.request_seq} command="{error.command}")'
            f'{f": {error.body.error}" if error.body is not None and error.body.error else ""}'
        )
        self.error = error


class DebugAdapterRPCErrorException(JsonRPCException):
    def __init__(
        self,
        message: Optional[str] = None,
        request_seq: int = -1,
        command: str = "",
        success: Optional[bool] = None,
        error_message: Optional[Message] = None,
    ) -> None:
        super().__init__(
            f'{(message + " ") if message else ""}(seq={request_seq} command="{command}")'
            f'{f": {error_message}" if error_message else ""}'
        )
        self.message = message
        self.request_seq = request_seq
        self.command = command
        self.success = success
        self.error_message = error_message


TResult = TypeVar("TResult", bound=Any)


class DebugAdapterProtocol(JsonRPCProtocolBase):
    _logger = LoggingDescriptor()

    def __init__(self) -> None:
        super().__init__()
        self._sended_request_lock = threading.RLock()
        self._sended_request: OrderedDict[int, SendedRequestEntry] = OrderedDict()
        self._received_request_lock = threading.RLock()
        self._received_request: OrderedDict[int, asyncio.Future[Any]] = OrderedDict()
        self._initialized = False
        self._running_handle_message_tasks: Set[asyncio.Future[Any]] = set()

    @_logger.call
    def send_message(self, message: ProtocolMessage) -> None:
        body = as_json(message, compact=True).encode(self.CHARSET)

        header = (f"Content-Length: {len(body)}\r\n\r\n").encode("ascii")
        if self.write_transport is not None:
            msg = header + body

            if self._loop:
                self.write_transport.write(msg)

    def send_error(
        self,
        message: Optional[str] = None,
        request_seq: int = -1,
        command: str = "",
        success: Optional[bool] = None,
        error_message: Optional[Message] = None,
    ) -> None:
        self.send_message(
            ErrorResponse(
                success=success or False,
                request_seq=request_seq,
                message=message,
                command=command,
                body=ErrorBody(error=error_message),
            )
        )

    @staticmethod
    def _generate_json_rpc_messages_from_dict(
        data: Union[Dict[Any, Any], List[Dict[Any, Any]]],
    ) -> Iterator[ProtocolMessage]:
        def inner(d: Dict[Any, Any]) -> ProtocolMessage:
            result = from_dict(d, (Request, Response, Event))
            if isinstance(result, Response) and not result.success:
                return from_dict(d, ErrorResponse)
            return result

        if isinstance(data, list):
            for e in data:
                yield inner(e)
        else:
            yield inner(data)

    def _handle_body(self, body: bytes, charset: str) -> None:
        try:
            self._handle_messages(self._generate_json_rpc_messages_from_dict(json.loads(body.decode(charset))))
        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._logger.exception(e)
            self.send_error(
                f"Invalid Message: {type(e).__name__}: {e!s} -> {body!s}\n{traceback.format_exc()}",
                error_message=Message(traceback.format_exc()),
            )

    def _handle_messages(self, iterator: Iterator[ProtocolMessage]) -> None:
        for m in iterator:
            task = asyncio.create_task(self.handle_message(m), name="handle_message")
            self._running_handle_message_tasks.add(task)
            task.add_done_callback(self._running_handle_message_tasks.discard)

    @_logger.call
    async def handle_message(self, message: ProtocolMessage) -> None:
        if isinstance(message, Request):
            self.handle_request(message)
        if isinstance(message, Event):
            self.handle_event(message)
        elif isinstance(message, ErrorResponse):
            self.handle_error_response(message)
        elif isinstance(message, Response):
            self.handle_response(message)

    @staticmethod
    def _convert_params(
        callable: Callable[..., Any],
        param_type: Optional[Type[Any]],
        params: Any,
    ) -> Tuple[List[Any], Dict[str, Any]]:
        if params is None:
            return [], {}
        if param_type is None:
            if isinstance(params, Mapping):
                return [], dict(**params)

            return [params], {}

        converted_params = from_dict(params, param_type)

        signature = inspect.signature(callable)

        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())

        kw_args = {}
        args = []
        params_added = False
        rest = set(converted_params.__dict__.keys())
        if isinstance(params, dict):
            rest = set.union(rest, params.keys())

        for v in signature.parameters.values():
            if v.name in converted_params.__dict__:
                if v.kind == inspect.Parameter.POSITIONAL_ONLY:
                    args.append(getattr(converted_params, v.name))
                else:
                    kw_args[v.name] = getattr(converted_params, v.name)
                rest.remove(v.name)
            elif v.name == "arguments":
                if v.kind == inspect.Parameter.POSITIONAL_ONLY:
                    args.append(converted_params)
                    params_added = True
                else:
                    kw_args[v.name] = converted_params
                    params_added = True
            elif isinstance(params, dict) and v.name in params:
                if v.kind == inspect.Parameter.POSITIONAL_ONLY:
                    args.append(params[v.name])
                else:
                    kw_args[v.name] = params[v.name]
        if has_var_kw:
            for r in rest:
                if hasattr(converted_params, r):
                    kw_args[r] = getattr(converted_params, r)
                elif isinstance(params, dict) and r in params:
                    kw_args[r] = params[r]

            if not params_added:
                kw_args["arguments"] = converted_params
        return args, kw_args

    async def handle_unknown_command(self, message: Request) -> Any:
        raise DebugAdapterRPCErrorException(
            f"Unknown Command '{message.command}'",
            error_message=Message(
                format='Unknown command "{command}": {request}',
                variables={"command": str(message.command), "request": str(message)},
                show_user=False,
            ),
        )

    @_logger.call
    def handle_request(self, message: Request) -> None:
        e = self.registry.get_entry(message.command)

        with self._received_request_lock:
            if e is None or not callable(e.method):
                result = asyncio.create_task(
                    self.handle_unknown_command(message),
                    name="handle_unknown_command",
                )
            else:
                params = self._convert_params(e.method, e.param_type, message.arguments)

                result = asyncio.create_task(
                    ensure_coroutine(e.method)(*params[0], **params[1]),
                    name=e.method.__name__,
                )

            self._received_request[message.seq] = result

        def done(t: "asyncio.Task[Any]") -> None:
            try:
                self.send_response(message.seq, message.command, t.result())
            except asyncio.CancelledError:
                self._logger.debug(lambda: f"request message {message!r} canceled")
            except (SystemExit, KeyboardInterrupt):
                raise
            except DebugAdapterRPCErrorException as ex:
                self.send_error(
                    message=ex.message,
                    request_seq=message.seq,
                    command=ex.command or message.command,
                    success=ex.success or False,
                    error_message=ex.error_message,
                )
            except DebugAdapterErrorResponseError as ex:
                self.send_error(
                    ex.error.message,
                    message.seq,
                    message.command,
                    False,
                    error_message=ex.error.body.error if ex.error.body is not None else None,
                )
            except BaseException as e:
                self._logger.exception(e)
                self.send_error(
                    str(type(e).__name__),
                    message.seq,
                    message.command,
                    False,
                    error_message=Message(format=f"{type(e).__name__}: {e}"),
                )
            finally:
                with self._received_request_lock:
                    self._received_request.pop(message.seq, None)

        result.add_done_callback(done)

    @_logger.call
    def send_response(
        self,
        request_seq: int,
        command: str,
        result: Optional[Any] = None,
        success: bool = True,
        message: Optional[str] = None,
    ) -> None:
        self.send_message(
            Response(
                request_seq=request_seq,
                command=command,
                success=success,
                message=message,
                body=result,
            )
        )

    @_logger.call
    def send_request(self, request: Request, return_type: Optional[Type[TResult]] = None) -> Task[TResult]:
        result: Task[TResult] = Task()

        with self._sended_request_lock:
            self._sended_request[request.seq] = SendedRequestEntry(result, return_type)

        self.send_message(request)

        return result

    @_logger.call
    def send_request_async(
        self, request: Request, return_type: Optional[Type[TResult]] = None
    ) -> "asyncio.Future[TResult]":
        return asyncio.wrap_future(self.send_request(request, return_type))

    @_logger.call
    def send_event(self, event: Event) -> None:
        self.send_message(event)

    @_logger.call
    async def send_event_async(self, event: Event) -> None:
        self.send_event(event)

    @_logger.call
    def handle_error_response(self, message: ErrorResponse) -> None:
        with self._sended_request_lock:
            entry = self._sended_request.pop(message.request_seq, None)

        exception = DebugAdapterErrorResponseError(message)
        if entry is None:
            raise exception

        entry.future.set_exception(exception)

    @_logger.call
    def handle_response(self, message: Response) -> None:
        with self._sended_request_lock:
            entry = self._sended_request.pop(message.request_seq, None)

        if entry is None:
            error = f"Invalid response. Could not find id '{message.request_seq}' in request list {message!r}"
            self._logger.warning(error)
            self.send_error(
                "invalid response",
                error_message=Message(format=error, show_user=True),
            )
            return

        try:
            if message.success:
                if not entry.future.done():
                    entry.future.set_result(from_dict(message.body, entry.result_type))
            else:
                raise DebugAdapterErrorResponseError(ErrorResponse(**as_dict(message)))
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            if not entry.future.done():
                entry.future.set_exception(e)

    @_logger.call
    def handle_event(self, message: Event) -> None:
        raise NotImplementedError
