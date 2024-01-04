from typing import List, Optional, Sequence, Set, Tuple

import click

from robotcode.core.types import ServerMode
from robotcode.plugin import Application
from robotcode.plugin.click_helper.types import (
    AddressesPort,
    AddressParamType,
    AddressPortParamType,
    EnumChoice,
    MutuallyExclusiveOption,
    NameParamType,
    PortParamType,
)

from .types import FC

# mypy: disable-error-code="attr-defined"


def server_options(
    default_server_mode: ServerMode,
    default_port: int,
    allowed_server_modes: Optional[Set[ServerMode]] = None,
) -> Sequence[FC]:
    result: List[FC] = []

    def exclusive(option_name: str, *args: ServerMode) -> Sequence[str]:
        return (
            [option_name]
            if not allowed_server_modes or any(True for arg in args if arg in allowed_server_modes)
            else []
        )

    if not allowed_server_modes or ServerMode.STDIO in allowed_server_modes:
        result += [
            click.option(
                "--stdio",
                "stdio",
                cls=MutuallyExclusiveOption,
                mutually_exclusive={
                    *exclusive("bind", ServerMode.TCP, ServerMode.SOCKET),
                    "mode",
                    *exclusive("pipe", ServerMode.PIPE),
                    *exclusive("pipe-name", ServerMode.PIPE, ServerMode.PIPE_SERVER),
                    *exclusive("pipe-server", ServerMode.PIPE_SERVER),
                    *exclusive("port", ServerMode.TCP, ServerMode.SOCKET),
                    *exclusive("socket", ServerMode.SOCKET),
                    *exclusive("tcp", ServerMode.TCP),
                },
                type=bool,
                default=False,
                is_flag=True,
                help="Run in `stdio` mode. (Equivalent to `--mode stdio`)",
                show_envvar=True,
            )
        ]
    if not allowed_server_modes or ServerMode.TCP in allowed_server_modes:
        result += [
            click.option(
                "--tcp",
                "tcp",
                cls=MutuallyExclusiveOption,
                mutually_exclusive={
                    "mode",
                    *exclusive("pipe", ServerMode.PIPE),
                    *exclusive("pipe-name", ServerMode.PIPE, ServerMode.PIPE_SERVER),
                    *exclusive("pipe-server", ServerMode.PIPE_SERVER),
                    *exclusive("port", ServerMode.TCP, ServerMode.SOCKET),
                    *exclusive("socket", ServerMode.SOCKET),
                    *exclusive("stdio", ServerMode.STDIO),
                },
                type=AddressPortParamType(),
                show_default=True,
                help="Run in `tcp` server mode and listen at the given port. "
                "(Equivalent to `--mode tcp --port <port>`)",
            )
        ]
    if not allowed_server_modes or ServerMode.SOCKET in allowed_server_modes:
        result += [
            click.option(
                "--socket",
                "socket",
                cls=MutuallyExclusiveOption,
                mutually_exclusive={
                    "mode",
                    *exclusive("pipe", ServerMode.PIPE),
                    *exclusive("pipe-name", ServerMode.PIPE, ServerMode.PIPE_SERVER),
                    *exclusive("pipe-server", ServerMode.PIPE_SERVER),
                    *exclusive("port", ServerMode.TCP, ServerMode.SOCKET),
                    *exclusive("stdio", ServerMode.STDIO),
                    *exclusive("tcp", ServerMode.TCP),
                },
                type=AddressPortParamType(),
                show_default=True,
                help="Run in `socket` mode and connect to the given port. "
                "(Equivalent to `--mode socket --port <port>`)",
            )
        ]
    if not allowed_server_modes or ServerMode.PIPE in allowed_server_modes:
        result += [
            click.option(
                "--pipe",
                "pipe",
                cls=MutuallyExclusiveOption,
                mutually_exclusive={
                    *exclusive("bind", ServerMode.TCP, ServerMode.SOCKET),
                    "mode",
                    *exclusive("pipe-name", ServerMode.PIPE, ServerMode.PIPE_SERVER),
                    *exclusive("pipe-server", ServerMode.PIPE_SERVER),
                    *exclusive("port", ServerMode.TCP, ServerMode.SOCKET),
                    *exclusive("socket", ServerMode.SOCKET),
                    *exclusive("stdio", ServerMode.STDIO),
                    *exclusive("tcp", ServerMode.TCP),
                },
                type=NameParamType(),
                help="Run in `pipe` mode and connect to the given pipe name. "
                "(Equivalent to `--mode pipe --pipe-name <name>`)",
            )
        ]
    if not allowed_server_modes or ServerMode.PIPE_SERVER in allowed_server_modes:
        result += [
            click.option(
                "--pipe-server",
                "pipe_server",
                cls=MutuallyExclusiveOption,
                mutually_exclusive={
                    *exclusive("bind", ServerMode.TCP, ServerMode.SOCKET),
                    "mode",
                    *exclusive("pipe", ServerMode.PIPE),
                    *exclusive("pipe-name", ServerMode.PIPE, ServerMode.PIPE_SERVER),
                    *exclusive("port", ServerMode.TCP, ServerMode.SOCKET),
                    *exclusive("socket", ServerMode.SOCKET),
                    *exclusive("stdio", ServerMode.STDIO),
                    *exclusive("tcp", ServerMode.TCP),
                },
                type=NameParamType(),
                help="Run in `pipe-server` mode and listen at the given pipe name. "
                "(Equivalent to `--mode pipe-server --pipe-name <name>`)",
            )
        ]

    result += [
        click.option(
            "--mode",
            "mode",
            cls=MutuallyExclusiveOption,
            mutually_exclusive={
                *exclusive("pipe", ServerMode.PIPE),
                *exclusive("pipe-server", ServerMode.PIPE_SERVER),
                *exclusive("socket", ServerMode.SOCKET),
                *exclusive("stdio", ServerMode.STDIO),
                *exclusive("tcp", ServerMode.TCP),
            },
            type=EnumChoice(
                ServerMode,
                excluded=None if allowed_server_modes is None else (set(ServerMode).difference(allowed_server_modes)),
            ),
            default=default_server_mode,
            show_default=True,
            help="The mode to use for the debug launch server.",
            show_envvar=True,
        )
    ]

    if not allowed_server_modes or ServerMode.TCP in allowed_server_modes or ServerMode.SOCKET in allowed_server_modes:
        result += [
            click.option(
                "--port",
                "port",
                cls=MutuallyExclusiveOption,
                mutually_exclusive={
                    *exclusive("pipe", ServerMode.PIPE),
                    *exclusive("pipe-server", ServerMode.PIPE_SERVER),
                    *exclusive("pipe-name", ServerMode.PIPE, ServerMode.PIPE_SERVER),
                },
                type=PortParamType(),
                default=default_port,
                show_default=True,
                help="The port to listen on or connect to. (Only valid for `tcp` and `socket mode`)",
                show_envvar=True,
            ),
            click.option(
                "--bind",
                "bind",
                cls=MutuallyExclusiveOption,
                mutually_exclusive={
                    *exclusive("pipe", ServerMode.PIPE),
                    *exclusive("pipe-server", ServerMode.PIPE_SERVER),
                    *exclusive("pipe-name", ServerMode.PIPE, ServerMode.PIPE_SERVER),
                },
                type=AddressParamType(),
                default=["127.0.0.1"],
                show_default=True,
                help="Specify alternate bind address. If no address is specified `localhost` is used. "
                "(Only valid for tcp and socket mode)",
                show_envvar=True,
                multiple=True,
            ),
        ]

    if (
        not allowed_server_modes
        or ServerMode.PIPE in allowed_server_modes
        or ServerMode.PIPE_SERVER in allowed_server_modes
    ):
        result += [
            click.option(
                "--pipe-name",
                "pipe_name",
                cls=MutuallyExclusiveOption,
                mutually_exclusive={
                    *exclusive("bind", ServerMode.TCP, ServerMode.SOCKET),
                    *exclusive("pipe", ServerMode.PIPE),
                    *exclusive("pipe-server", ServerMode.PIPE_SERVER),
                    *exclusive("port", ServerMode.TCP, ServerMode.SOCKET),
                    *exclusive("socket", ServerMode.SOCKET),
                    *exclusive("stdio", ServerMode.STDIO),
                    *exclusive("tcp", ServerMode.TCP),
                },
                type=NameParamType(),
                default=None,
                help="The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode)",
                show_envvar=True,
            )
        ]

    return result


def resolve_server_options(
    ctx: click.Context,
    app: Application,
    mode: ServerMode,
    port: Optional[int],
    bind: Optional[Sequence[str]],
    pipe_name: Optional[str],
    tcp: Optional[AddressesPort],
    socket: Optional[AddressesPort],
    stdio: Optional[bool],
    pipe: Optional[str],
    pipe_server: Optional[str],
) -> Tuple[ServerMode, Optional[int], Optional[Sequence[str]], Optional[str]]:
    if stdio and ctx.get_parameter_source("stdio") not in [
        click.core.ParameterSource.DEFAULT,
        click.core.ParameterSource.DEFAULT_MAP,
    ]:
        mode = ServerMode.STDIO

    if bind is None:
        bind = []

    if tcp is not None and ctx.get_parameter_source("tcp") not in [
        click.core.ParameterSource.DEFAULT,
        click.core.ParameterSource.DEFAULT_MAP,
    ]:
        mode = ServerMode.TCP
        if tcp.port is not None:
            port = tcp.port
        if tcp.addresses is not None:
            bind = [*bind, *tcp.addresses]

    if socket is not None and ctx.get_parameter_source("socket") not in [
        click.core.ParameterSource.DEFAULT,
        click.core.ParameterSource.DEFAULT_MAP,
    ]:
        mode = ServerMode.SOCKET
        if socket.port is not None:
            port = socket.port
        if socket.addresses is not None:
            bind = [*bind, *socket.addresses]

    if pipe is not None and ctx.get_parameter_source("pipe") not in [
        click.core.ParameterSource.DEFAULT,
        click.core.ParameterSource.DEFAULT_MAP,
    ]:
        mode = ServerMode.PIPE
        pipe_name = pipe

    if pipe_server is not None and ctx.get_parameter_source("pipe_server") not in [
        click.core.ParameterSource.DEFAULT,
        click.core.ParameterSource.DEFAULT_MAP,
    ]:
        mode = ServerMode.PIPE_SERVER
        pipe_name = pipe_server

    app.verbose(lambda: f"Mode: {mode}")
    app.verbose(lambda: f"Port: {port}")
    if bind:
        app.verbose(lambda: f"Addresses: {bind}")
    if pipe_name:
        app.verbose(lambda: f"Pipe Name: {pipe_name}")
    if app.config.launcher_script:
        app.verbose(lambda: f"Launcher Script: {app.config.launcher_script}")

    return mode, port, bind, pipe_name
