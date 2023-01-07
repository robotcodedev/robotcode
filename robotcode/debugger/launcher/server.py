from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from ...jsonrpc2.protocol import rpc_method
from ...jsonrpc2.server import JsonRPCServer, JsonRpcServerMode, TcpParams
from ...language_server.robotframework.utils.version import get_robot_version
from ...utils.logging import LoggingDescriptor
from ..client import DAPClient, DAPClientError
from ..dap_types import (
    AttachRequest,
    AttachRequestArguments,
    Capabilities,
    ConfigurationDoneArguments,
    ConfigurationDoneRequest,
    DisconnectArguments,
    DisconnectRequest,
    Event,
    ExceptionBreakpointsFilter,
    InitializeRequest,
    InitializeRequestArguments,
    LaunchRequestArguments,
    OutputCategory,
    OutputEvent,
    OutputEventBody,
    Request,
    RunInTerminalKind,
    RunInTerminalRequest,
    RunInTerminalRequestArguments,
    RunInTerminalResponseBody,
    TerminateArguments,
    TerminatedEvent,
    TerminateRequest,
)
from ..protocol import DebugAdapterProtocol


class OutputProtocol(asyncio.SubprocessProtocol):
    def __init__(self, parent: LauncherDebugAdapterProtocol) -> None:
        super().__init__()
        self.parent = parent

    def pipe_data_received(self, fd: Any, data: bytes) -> None:
        category = None

        if fd == 1:
            category = OutputCategory.STDOUT
        elif fd == 2:
            category = OutputCategory.STDERR

        self.parent.send_event(OutputEvent(body=OutputEventBody(output=data.decode(), category=category)))


class LauncherDebugAdapterProtocol(DebugAdapterProtocol):
    _logger = LoggingDescriptor()

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[DAPClient] = None
        self._process: Optional[asyncio.subprocess.Process] = None
        self._initialize_arguments: Optional[InitializeRequestArguments] = None

    @property
    def client(self) -> DAPClient:
        if self._client is None:
            raise DAPClientError("Client not defined.")

        return self._client

    @client.setter
    def client(self, value: DAPClient) -> None:
        self._client = value

    @property
    def connected(self) -> bool:
        return self._client is not None and self._client.connected

    @rpc_method(name="initialize", param_type=InitializeRequestArguments)
    async def _initialize(self, arguments: InitializeRequestArguments, *args: Any, **kwargs: Any) -> Capabilities:
        self._initialize_arguments = arguments

        self._initialized = True

        return Capabilities(
            supports_configuration_done_request=True,
            supports_conditional_breakpoints=True,
            supports_hit_conditional_breakpoints=True,
            support_terminate_debuggee=True,
            # support_suspend_debuggee=True,
            supports_evaluate_for_hovers=True,
            supports_terminate_request=True,
            supports_log_points=True,
            supports_set_expression=True,
            supports_set_variable=True,
            supports_value_formatting_options=True,
            exception_breakpoint_filters=[
                ExceptionBreakpointsFilter(
                    filter="failed_keyword",
                    label="Failed Keywords",
                    description="Breaks on failed keywords",
                    default=False,
                ),
                ExceptionBreakpointsFilter(
                    filter="uncaught_failed_keyword",
                    label="Uncaught Failed Keywords",
                    description="Breaks on uncaught failed keywords",
                    default=True,
                ),
                ExceptionBreakpointsFilter(
                    filter="failed_test",
                    label="Failed Test",
                    description="Breaks on failed tests",
                    default=False,
                ),
                ExceptionBreakpointsFilter(
                    filter="failed_suite",
                    label="Failed Suite",
                    description="Breaks on failed suite",
                    default=False,
                ),
            ],
            supports_exception_options=True,
            supports_exception_filter_options=True,
        )

    @rpc_method(name="launch", param_type=LaunchRequestArguments)
    async def _launch(
        self,
        request: str,
        python: str,
        cwd: str = ".",
        target: Optional[str] = None,
        paths: Optional[List[str]] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, Optional[Any]]] = None,
        console: Optional[Literal["internalConsole", "integratedTerminal", "externalTerminal"]] = "integratedTerminal",
        name: Optional[str] = None,
        no_debug: Optional[bool] = None,
        robotPythonPath: Optional[List[str]] = None,  # noqa: N803
        launcherArgs: Optional[List[str]] = None,  # noqa: N803
        launcherTimeout: Optional[int] = None,  # noqa: N803
        debuggerArgs: Optional[List[str]] = None,  # noqa: N803
        debuggerTimeout: Optional[int] = None,  # noqa: N803
        attachPython: Optional[bool] = False,  # noqa: N803
        variables: Optional[Dict[str, Any]] = None,
        outputDir: Optional[str] = None,
        outputMessages: Optional[bool] = False,
        outputLog: Optional[bool] = False,
        groupOutput: Optional[bool] = False,
        stopOnEntry: Optional[bool] = False,  # noqa: N803
        dryRun: Optional[bool] = None,
        mode: Optional[str] = None,
        variableFiles: Optional[List[str]] = None,
        languages: Optional[List[str]] = None,
        arguments: Optional[LaunchRequestArguments] = None,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        from ...utils.net import find_free_port

        connect_timeout = launcherTimeout or 10

        port = find_free_port()

        launcher = Path(Path(__file__).parent.parent)

        run_args = [python, "-u", str(launcher)]

        run_args += ["-p", str(port)]

        run_args += ["-w"]

        if debuggerTimeout is not None:
            run_args += ["-t", str(debuggerTimeout)]

        if no_debug:
            run_args += ["-n"]

        if attachPython and not no_debug:
            run_args += ["-d", "-dp", str(find_free_port()), "-dw"]

        if outputMessages:
            run_args += ["-om"]

        if outputLog:
            run_args += ["-ol"]

        if groupOutput:
            run_args += ["-og"]

        if stopOnEntry:
            run_args += ["-soe"]

        run_args += debuggerArgs or []

        run_args += ["--"]

        if get_robot_version() >= (6, 0) and languages:
            for lang in languages:
                run_args += ["--language", lang]

        if mode:
            if mode == "rpa":
                run_args += ["--rpa"]
            elif mode == "norpa":
                run_args += ["--norpa"]

        if dryRun:
            run_args += ["--dryrun"]

        if outputDir:
            run_args += ["-d", outputDir]

        if robotPythonPath:
            for e in robotPythonPath:
                run_args += ["-P", e]

        if variableFiles:
            for v in variableFiles:
                run_args += ["-V", v]

        if variables:
            for k, v in variables.items():
                run_args += ["-v", f"{k}:{v}"]

        if include:
            for v in include:
                run_args += ["-i", f"{v}"]

        if exclude:
            for v in exclude:
                run_args += ["-e", f"{v}"]

        run_args += args or []

        if paths:
            for p in paths:
                run_args.append(p)

        if target:
            run_args.append(target)

        if target is not None and not paths and not target:
            run_args.append(".")

        env = {k: ("" if v is None else str(v)) for k, v in env.items()} if env else {}

        if console in ["integratedTerminal", "externalTerminal"]:
            await self.send_request_async(
                RunInTerminalRequest(
                    arguments=RunInTerminalRequestArguments(
                        cwd=cwd,
                        args=run_args,
                        env=env,
                        kind=RunInTerminalKind.INTEGRATED
                        if console == "integratedTerminal"
                        else RunInTerminalKind.EXTERNAL
                        if console == "externalTerminal"
                        else None,
                        title=name,
                    )
                ),
                return_type=RunInTerminalResponseBody,
            )
        elif console is None or console in ["internalConsole"]:
            run_env: Dict[str, Optional[str]] = dict(os.environ)
            run_env.update(env)

            await asyncio.get_event_loop().subprocess_exec(
                lambda: OutputProtocol(self),
                *run_args,
                cwd=cwd,
                env=run_env,
            )

        else:
            raise ValueError(f'Unknown console type "{console}".')

        self.client = DAPClient(self, TcpParams(None, port))
        try:
            await self.client.connect(connect_timeout)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError("Can't connect to debugger.")

        if self._initialize_arguments is not None:
            await self.client.protocol.send_request_async(InitializeRequest(arguments=self._initialize_arguments))

    @rpc_method(name="configurationDone", param_type=ConfigurationDoneArguments)
    async def _configuration_done(
        self, arguments: Optional[ConfigurationDoneArguments] = None, *args: Any, **kwargs: Any
    ) -> None:
        await self.client.protocol.send_request_async(ConfigurationDoneRequest(arguments=arguments))
        await self.client.protocol.send_request_async(AttachRequest(arguments=AttachRequestArguments()))

    @rpc_method(name="disconnect", param_type=DisconnectArguments)
    async def _disconnect(self, arguments: Optional[DisconnectArguments] = None, *args: Any, **kwargs: Any) -> None:
        if self.connected:
            if not self.client.protocol.terminated:
                await self.client.protocol.send_request_async(DisconnectRequest(arguments=arguments))
        else:
            self.send_event(Event("disconnectRequested"))
            await self.send_event_async(TerminatedEvent())

    @_logger.call
    @rpc_method(name="terminate", param_type=TerminateArguments)
    async def _terminate(self, arguments: Optional[TerminateArguments] = None, *args: Any, **kwargs: Any) -> None:
        if self.client.connected:
            return await self.client.protocol.send_request_async(TerminateRequest(arguments=arguments))
        else:
            self.send_event(Event("terminateRequested"))
            await self.send_event_async(TerminatedEvent())

    async def handle_unknown_command(self, message: Request) -> Any:
        if self.connected:
            self._logger.debug("Forward request to client...")

            return await self.client.protocol.send_request_async(message)

        return await super().handle_unknown_command(message)


TCP_DEFAULT_PORT = 6611


class LauncherServer(JsonRPCServer[LauncherDebugAdapterProtocol]):
    def __init__(
        self,
        mode: JsonRpcServerMode = JsonRpcServerMode.STDIO,
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
    ):
        super().__init__(
            mode=mode,
            tcp_params=tcp_params,
        )

    def create_protocol(self) -> LauncherDebugAdapterProtocol:
        return LauncherDebugAdapterProtocol()
