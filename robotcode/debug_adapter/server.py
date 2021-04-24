from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from ..jsonrpc2.protocol import rpc_method
from ..jsonrpc2.server import JsonRPCServer, JsonRpcServerMode, TcpParams
from ..utils.logging import LoggingDescriptor
from .client import ClientNotConnectedError, DAPClient
from .protocol import DebugAdapterProtocol
from .types import (
    Capabilities,
    ConfigurationDoneArguments,
    DisconnectArguments,
    InitializeRequestArguments,
    LaunchRequestArguments,
    RunInTerminalRequest,
    RunInTerminalRequestArguments,
    RunInTerminalResponseBody,
    SetBreakpointsArguments,
    SetBreakpointsResponseBody,
    TerminatedEvent,
    ThreadsResponseBody,
)


class DAPServerProtocol(DebugAdapterProtocol):
    _logger = LoggingDescriptor()

    def __init__(self) -> None:
        super().__init__()
        self._client: Optional[DAPClient] = None

    @property
    def client(self) -> DAPClient:
        if self._client is None:
            raise ClientNotConnectedError("Client not defined.")

        return self._client

    @client.setter
    def client(self, value: DAPClient) -> None:
        self._client = value

    @rpc_method(name="initialize", param_type=InitializeRequestArguments)
    async def _initialize(self, arguments: InitializeRequestArguments) -> Capabilities:
        self._initialized = True

        return Capabilities(
            supports_configuration_done_request=True,
            # supports_function_breakpoints=True,
            # supports_conditional_breakpoints=True,
            # supports_hit_conditional_breakpoints=True,
            # support_terminate_debuggee=True,
            # support_suspend_debuggee=True,
            # supports_loaded_sources_request=True,
            # supports_terminate_request=True,
            # supports_data_breakpoints=True
        )

    @rpc_method(name="launch", param_type=LaunchRequestArguments)
    async def _launch(
        self,
        request: str,
        python: str,
        cwd: str = ".",
        target: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, Optional[str]]] = None,
        console: Optional[Literal["integrated", "external"]] = "integrated",
        name: Optional[str] = None,
        no_debug: Optional[bool] = None,
        pythonPath: Optional[List[str]] = None,  # noqa: N803
        variables: Optional[Dict[str, Any]] = None,
        arguments: Optional[LaunchRequestArguments] = None,
        **kwargs: Any,
    ) -> None:
        from ..utils.debugpy import find_free_port

        port = find_free_port()

        runner = Path(Path(__file__).parent, "runner")

        run_args = [python, "-u", str(runner)]

        run_args += ["-p", str(port)]
        run_args += ["--debugpy"]
        # run_args += ["--debugpy-wait-for-client"]

        run_args += ["--"]

        run_args += args or []

        if pythonPath:
            for e in pythonPath:
                run_args += ["-P", e]

        if variables:
            for k, v in variables.items():
                run_args += ["-v", f"{k}:{v}"]

        if target:
            run_args.append(target)

        await self.send_request_async(
            RunInTerminalRequest(
                arguments=RunInTerminalRequestArguments(
                    cwd=cwd,
                    args=run_args,
                    env=env,
                    kind=console if console in ["integrated", "external"] else None,
                    title=name,
                )
            ),
            return_type=RunInTerminalResponseBody,
        )

        self.client = DAPClient(self, TcpParams(None, port))
        try:
            await self.client.connect()
        except asyncio.TimeoutError:
            self.send_event(TerminatedEvent())

    @rpc_method(name="configurationDone", param_type=ConfigurationDoneArguments)
    async def _configuration_done(self, arguments: Optional[ConfigurationDoneArguments] = None) -> None:
        # TODO
        pass

    @rpc_method(name="disconnect", param_type=DisconnectArguments)
    async def _disconnect(self, arguments: Optional[DisconnectArguments] = None) -> None:
        # TODO
        pass

    @rpc_method(name="setBreakpoints", param_type=SetBreakpointsArguments)
    async def _set_breakpoints(self, arguments: Optional[SetBreakpointsArguments] = None) -> SetBreakpointsResponseBody:
        # TODO
        return SetBreakpointsResponseBody(breakpoints=[])

    @rpc_method(name="threads")
    async def _threads(self) -> ThreadsResponseBody:
        # TODO
        return ThreadsResponseBody(threads=[])


TCP_DEFAULT_PORT = 6611


class DebugAdapterServer(JsonRPCServer[DAPServerProtocol]):
    def __init__(
        self,
        mode: JsonRpcServerMode = JsonRpcServerMode.STDIO,
        tcp_params: TcpParams = TcpParams(None, TCP_DEFAULT_PORT),
    ):
        super().__init__(
            mode=mode,
            tcp_params=tcp_params,
        )

    def create_protocol(self) -> DAPServerProtocol:
        return DAPServerProtocol()
