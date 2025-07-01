import asyncio
import os
import signal
import threading
from typing import Any, Callable, Dict, List, Literal, Optional, Union

from robotcode.core import concurrent
from robotcode.core.types import ServerMode, TcpParams
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.jsonrpc2.server import JsonRPCServer

from .dap_types import (
    AttachRequestArguments,
    Capabilities,
    CompletionsArguments,
    CompletionsResponseBody,
    ConfigurationDoneArguments,
    ContinueArguments,
    ContinueResponseBody,
    DisconnectArguments,
    EvaluateArgumentContext,
    EvaluateArguments,
    EvaluateResponseBody,
    Event,
    ExitedEvent,
    ExitedEventBody,
    InitializedEvent,
    InitializeRequestArguments,
    NextArguments,
    PauseArguments,
    ScopesArguments,
    ScopesResponseBody,
    SetBreakpointsArguments,
    SetBreakpointsResponseBody,
    SetExceptionBreakpointsArguments,
    SetExceptionBreakpointsResponseBody,
    SetVariableArguments,
    SetVariableResponseBody,
    StackTraceArguments,
    StackTraceResponseBody,
    StepInArguments,
    StepOutArguments,
    TerminateArguments,
    TerminatedEvent,
    ThreadsResponseBody,
    ValueFormat,
    VariablesArguments,
    VariablesResponseBody,
)
from .debugger import Debugger, PathMapping
from .default_capabilities import DFEAULT_CAPABILITIES
from .protocol import DebugAdapterProtocol

TCP_DEFAULT_PORT = 6612


class DebugAdapterServerProtocol(DebugAdapterProtocol):
    _logger = LoggingDescriptor()

    def __init__(self) -> None:
        super().__init__()

        self._connected_event = threading.Event()
        self._disconnected_event = threading.Event()
        self._connected = False
        self._sigint_signaled = False

        self._initialized = False
        self._initialized_event = threading.Event()

        self._exited_lock = concurrent.RLock()
        self._exited = False

        self._terminated_lock = concurrent.RLock()
        self._terminated = False

        self._received_configuration_done_event = threading.Event()
        self._received_configuration_done = False
        self.received_configuration_done_callback: Optional[Callable[[], None]] = None

        Debugger.instance().send_event.add(self.on_debugger_send_event)

    def on_debugger_send_event(self, sender: Any, event: Event) -> None:
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self.send_event_async(event), loop=self._loop)

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def exited(self) -> bool:
        with self._exited_lock:
            return self._exited

    @property
    def terminated(self) -> bool:
        with self._terminated_lock:
            return self._terminated

    @_logger.call
    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        if self.connected:
            raise ConnectionError("Protocol already connected, only one conntection allowed.")

        super().connection_made(transport)

        if self.read_transport is not None and self.write_transport is not None:
            self._connected = True
            self._connected_event.set()

    @_logger.call
    def connection_lost(self, exc: Optional[BaseException]) -> None:
        super().connection_lost(exc)

        self._connected = False
        self._disconnected_event.set()

    @_logger.call
    def wait_for_client(self, timeout: float = 15) -> bool:
        if not self._connected_event.wait(timeout):
            raise TimeoutError("Timeout waiting for client")

        return self._connected

    @_logger.call
    def wait_for_initialized(self, timeout: float = 30) -> bool:
        if not self._initialized_event.wait(timeout):
            raise TimeoutError("Timeout waiting for client initialization")

        return self._initialized

    @_logger.call
    def wait_for_disconnected(self, timeout: float = 1) -> bool:
        self._disconnected_event.wait(timeout)

        return not self._connected

    @rpc_method(name="initialize", param_type=InitializeRequestArguments)
    async def _initialize(self, arguments: InitializeRequestArguments, *args: Any, **kwargs: Any) -> Capabilities:
        self._initialized = True

        if self.loop is not None:
            self.loop.call_soon(self.initialized)

        return DFEAULT_CAPABILITIES

    @rpc_method(name="attach", param_type=AttachRequestArguments)
    async def _attach(
        self,
        arguments: AttachRequestArguments,
        request: Optional[str] = None,
        type: Optional[str] = None,
        name: Optional[str] = None,
        restart: Optional[bool] = None,
        pathMappings: Optional[List[Dict[str, str]]] = None,  # noqa: N803
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if pathMappings:
            Debugger.instance().path_mappings = [
                PathMapping(
                    local_root=v.get("localRoot", None),
                    remote_root=v.get("remoteRoot", None),
                )
                for v in pathMappings
            ]
        Debugger.instance().attached = True

    @_logger.call
    def initialized(self) -> None:
        self.send_event(InitializedEvent())
        self._initialized_event.set()

    @_logger.call
    def exit(self, exit_code: int) -> None:
        with self._exited_lock:
            self.send_event(ExitedEvent(body=ExitedEventBody(exit_code=exit_code)))
            self._exited = True

    @_logger.call
    def terminate(self) -> None:
        with self._terminated_lock:
            self.send_event(TerminatedEvent())
            self._terminated = True

    @rpc_method(name="terminate", param_type=TerminateArguments)
    async def _terminate(
        self,
        arguments: Optional[TerminateArguments] = None,
        restart: Optional[bool] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        Debugger.instance().terminate()

        if not restart and not self._sigint_signaled:
            self._logger.debug("Send SIGINT to process")
            signal.raise_signal(signal.SIGINT)
            self._sigint_signaled = True

            Debugger.instance().continue_all_if_paused()
        else:
            await self.send_event_async(Event("terminateRequested"))

            self._logger.debug("Send SIGTERM to process")
            signal.raise_signal(signal.SIGTERM)

    @rpc_method(name="disconnect", param_type=DisconnectArguments)
    async def _disconnect(
        self,
        arguments: Optional[DisconnectArguments] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if (not (self.exited) or not (self.terminated)) and arguments is not None and arguments.terminate_debuggee:
            os._exit(-1)
        else:
            await self.send_event_async(Event("disconnectRequested"))
            Debugger.instance().attached = False
            Debugger.instance().continue_all()

    @rpc_method(name="setBreakpoints", param_type=SetBreakpointsArguments)
    async def _set_breakpoints(
        self, arguments: SetBreakpointsArguments, *args: Any, **kwargs: Any
    ) -> SetBreakpointsResponseBody:
        return SetBreakpointsResponseBody(
            breakpoints=Debugger.instance().set_breakpoints(
                arguments.source,
                arguments.breakpoints,
                arguments.lines,
                arguments.source_modified,
            )
        )

    @_logger.call
    @rpc_method(name="configurationDone", param_type=ConfigurationDoneArguments)
    async def _configuration_done(
        self,
        arguments: Optional[ConfigurationDoneArguments] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._received_configuration_done = True
        self._received_configuration_done_event.set()

        if self.received_configuration_done_callback is not None:
            self.received_configuration_done_callback()

    @_logger.call
    def wait_for_configuration_done(self, timeout: float = 5) -> bool:
        if not self._received_configuration_done_event.wait(timeout):
            raise TimeoutError("Timeout waiting for configuration done event")

        return self._received_configuration_done

    @rpc_method(name="continue", param_type=ContinueArguments)
    async def _continue(self, arguments: ContinueArguments, *args: Any, **kwargs: Any) -> ContinueResponseBody:
        Debugger.instance().continue_thread(arguments.thread_id)
        return ContinueResponseBody(all_threads_continued=True)

    @rpc_method(name="pause", param_type=PauseArguments)
    async def _pause(self, arguments: PauseArguments, *args: Any, **kwargs: Any) -> None:
        Debugger.instance().pause_thread(arguments.thread_id)

    @rpc_method(name="next", param_type=NextArguments)
    async def _next(self, arguments: NextArguments, *args: Any, **kwargs: Any) -> None:
        Debugger.instance().next(arguments.thread_id, arguments.granularity)

    @rpc_method(name="stepIn", param_type=StepInArguments)
    async def _step_in(self, arguments: StepInArguments, *args: Any, **kwargs: Any) -> None:
        Debugger.instance().step_in(arguments.thread_id, arguments.target_id, arguments.granularity)

    @rpc_method(name="stepOut", param_type=StepOutArguments)
    async def _step_out(self, arguments: StepOutArguments, *args: Any, **kwargs: Any) -> None:
        Debugger.instance().step_out(arguments.thread_id, arguments.granularity)

    @rpc_method(name="threads")
    async def _threads(self, *args: Any, **kwargs: Any) -> ThreadsResponseBody:
        return ThreadsResponseBody(threads=Debugger.instance().get_threads())

    @rpc_method(name="stackTrace", param_type=StackTraceArguments)
    async def _stack_trace(self, arguments: StackTraceArguments, *args: Any, **kwargs: Any) -> StackTraceResponseBody:
        result = Debugger.instance().get_stack_trace(
            arguments.thread_id,
            arguments.start_frame,
            arguments.levels,
            arguments.format,
        )
        return StackTraceResponseBody(stack_frames=result.stack_frames, total_frames=result.total_frames)

    @rpc_method(name="scopes", param_type=ScopesArguments)
    async def _scopes(self, arguments: ScopesArguments, *args: Any, **kwargs: Any) -> ScopesResponseBody:
        return ScopesResponseBody(scopes=Debugger.instance().get_scopes(arguments.frame_id))

    @rpc_method(name="variables", param_type=VariablesArguments)
    async def _variables(
        self,
        arguments: VariablesArguments,
        variables_reference: int,
        filter: Optional[Literal["indexed", "named"]] = None,
        start: Optional[int] = None,
        count: Optional[int] = None,
        format: Optional[ValueFormat] = None,
        *args: Any,
        **kwargs: Any,
    ) -> VariablesResponseBody:
        return VariablesResponseBody(
            variables=Debugger.instance().get_variables(variables_reference, filter, start, count, format)
        )

    @rpc_method(name="evaluate", param_type=EvaluateArguments)
    async def _evaluate(
        self,
        arguments: ScopesArguments,
        expression: str,
        frame_id: Optional[int] = None,
        context: Union[EvaluateArgumentContext, str, None] = None,
        format: Optional[ValueFormat] = None,
        *args: Any,
        **kwargs: Any,
    ) -> EvaluateResponseBody:
        result = Debugger.instance().evaluate(expression, frame_id, context, format)
        return EvaluateResponseBody(
            result=result.result,
            type=result.type,
            presentation_hint=result.presentation_hint,
            variables_reference=result.variables_reference,
            named_variables=result.named_variables,
            indexed_variables=result.indexed_variables,
            memory_reference=result.memory_reference,
        )

    @rpc_method(name="setVariable", param_type=SetVariableArguments)
    async def _set_variable(
        self,
        arguments: SetVariableArguments,
        variables_reference: int,
        name: str,
        value: str,
        format: Optional[ValueFormat] = None,
        *args: Any,
        **kwargs: Any,
    ) -> SetVariableResponseBody:
        result = Debugger.instance().set_variable(variables_reference, name, value, format)
        return SetVariableResponseBody(
            value=result.value,
            type=result.type,
            variables_reference=result.variables_reference,
            named_variables=result.named_variables,
            indexed_variables=result.indexed_variables,
        )

    @rpc_method(
        name="setExceptionBreakpoints",
        param_type=SetExceptionBreakpointsArguments,
    )
    async def _set_exception_breakpoints(
        self,
        arguments: SetExceptionBreakpointsArguments,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[SetExceptionBreakpointsResponseBody]:
        result = Debugger.instance().set_exception_breakpoints(
            arguments.filters,
            arguments.filter_options,
            arguments.exception_options,
        )
        return SetExceptionBreakpointsResponseBody(breakpoints=result) if result else None

    @rpc_method(name="completions", param_type=CompletionsArguments)
    async def _completions(
        self,
        arguments: CompletionsArguments,
        text: str,
        column: int,
        line: Optional[int] = None,
        frame_id: Optional[int] = None,
        *args: Any,
        **kwargs: Any,
    ) -> CompletionsResponseBody:
        result = Debugger.instance().completions(text, column, line, frame_id)
        return CompletionsResponseBody(targets=result)


class DebugAdapterServer(JsonRPCServer[DebugAdapterServerProtocol]):
    def __init__(
        self,
        mode: ServerMode = ServerMode.TCP,
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
        pipe_name: Optional[str] = None,
    ):
        super().__init__(mode=mode, tcp_params=tcp_params, pipe_name=pipe_name)
        self.protocol = DebugAdapterServerProtocol()

    def create_protocol(self) -> DebugAdapterServerProtocol:
        return self.protocol
