from typing import Optional, Sequence

import click
from robotcode.core.types import ServerMode
from robotcode.core.utils.cli import show_hidden_arguments
from robotcode.plugin import Application, UnknownError, pass_application
from robotcode.plugin.click_helper.options import resolve_server_options, server_options
from robotcode.plugin.click_helper.types import (
    AddressesPort,
    add_options,
)

from ..__version__ import __version__
from .run import run_launcher

LAUNCHER_DEFAULT_PORT = 6611


@click.command(
    add_help_option=True,
    hidden=show_hidden_arguments(),
)
@add_options(*server_options(ServerMode.STDIO, default_port=LAUNCHER_DEFAULT_PORT))
@click.version_option(version=__version__, prog_name="RobotCode Launcher")
@pass_application
@click.pass_context
def debug_launch(
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
) -> None:
    """Launches a robotcode debug session."""

    mode, port, bind, pipe_name = resolve_server_options(
        ctx, app, mode, port, bind, pipe_name, tcp, socket, stdio, pipe, pipe_server
    )

    try:
        run_launcher(
            mode,
            bind or "127.0.0.1",
            port if port is not None else LAUNCHER_DEFAULT_PORT,
            pipe_name,
            debugger_script=app.config.launcher_script,
        )
    except SystemExit:
        raise
    except KeyboardInterrupt:
        app.keyboard_interrupt()
    except Exception as e:
        raise UnknownError(str(e)) from e
