from typing import Optional, Sequence, Tuple

import click

from robotcode.core.types import ServerMode
from robotcode.plugin import Application, UnknownError, pass_application
from robotcode.plugin.click_helper.options import (
    resolve_server_options,
    server_options,
)
from robotcode.plugin.click_helper.types import AddressesPort, add_options

from .__version__ import __version__

DEBUGGER_DEFAULT_PORT = 6612
DEBUGPY_DEFAULT_PORT = 5678


@click.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
)
@click.option(
    "--debug/--no-debug",
    is_flag=True,
    default=True,
    help="Enable/disable debug mode",
    show_default=True,
)
@click.option(
    "--stop-on-entry / --no-stop-on-entry",
    is_flag=True,
    help="Breaks into debugger when a robot framework run starts.",
    show_default=True,
)
@click.option(
    "--wait-for-client/--no-wait-for-client",
    is_flag=True,
    default=True,
    help="Waits until a debug client is connected.",
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--wait-for-client-timeout",
    type=float,
    default=15,
    help="Timeout in seconds for waiting for a connection with a debug client.",
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--configuration-done-timeout",
    type=float,
    default=15,
    help="Timeout to wait for a configuration from client.",
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--debugpy/--no-debugpy",
    is_flag=True,
    default=False,
    help="Enable/disable python debugging.",
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--debugpy-wait-for-client/--no-debugpy-wait-for-client",
    is_flag=True,
    default=True,
    help="Waits for a debugpy client to connect.",
    show_default=False,
    show_envvar=True,
)
@click.option(
    "--debugpy-port",
    type=int,
    default=DEBUGPY_DEFAULT_PORT,
    help="The port for the debugpy session.",
    show_default=True,
)
@click.option(
    "--output-messages / --no-output-messages",
    default=False,
    is_flag=True,
    help="Send output messages from robot framework to client.",
    show_default=True,
)
@click.option(
    "--output-log / --no-output-log",
    default=True,
    is_flag=True,
    help="Send log messages from robotframework to client.",
    show_default=True,
)
@click.option(
    "--output-timestamps / --no-output-timestamps",
    default=False,
    is_flag=True,
    help="Include timestamps in log and output messages.",
    show_default=True,
)
@click.option(
    "--group-output / --no-group-output",
    default=False,
    is_flag=True,
    help="Fold/group messages or log messages.",
    show_default=True,
)
@add_options(
    *server_options(
        ServerMode.TCP,
        default_port=DEBUGGER_DEFAULT_PORT,
        allowed_server_modes={ServerMode.TCP, ServerMode.PIPE_SERVER},
    )
)
@click.version_option(version=__version__, prog_name="RobotCode Debugger")
@click.argument("robot_options_and_args", nargs=-1, type=click.Path())
@pass_application
@click.pass_context
def debug(
    ctx: click.Context,
    app: Application,
    mode: ServerMode,
    port: Optional[int],
    bind: Optional[Sequence[str]],
    pipe_name: Optional[str],
    tcp: Optional[AddressesPort],
    pipe_server: Optional[str],
    debug: bool,
    wait_for_client: bool,
    wait_for_client_timeout: float,
    configuration_done_timeout: float,
    debugpy: bool,
    debugpy_wait_for_client: bool,
    debugpy_port: int,
    output_messages: bool,
    output_log: bool,
    output_timestamps: bool,
    group_output: bool,
    stop_on_entry: bool,
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """Starts a Robot Framework debug session and waits for incomming connections."""
    from .run import run_debugger

    mode, port, bind, pipe_name = resolve_server_options(
        ctx,
        app,
        mode,
        port,
        bind,
        pipe_name,
        tcp,
        None,
        None,
        None,
        pipe_server,
    )

    app.verbose(f"Debug Mode: {debug}")
    app.verbose(f"Wait for client: {wait_for_client}")
    app.verbose(f"Wait for client timeout: {wait_for_client_timeout}")
    app.verbose(f"Configuration done timeout: {configuration_done_timeout}")
    app.verbose(f"Debugpy: {debugpy}")
    app.verbose(f"Debugpy wait for client: {debugpy_wait_for_client}")
    app.verbose(f"Debugpy port: {debugpy_port}")
    app.verbose(f"Output messages: {output_messages}")
    app.verbose(f"Output log: {output_log}")
    app.verbose(f"Output timestamps: {output_timestamps}")
    app.verbose(f"Group output: {group_output}")
    app.verbose(f"Stop in entry: {stop_on_entry}")
    app.verbose(f"Robot options and args: {robot_options_and_args}")

    try:
        app.exit(
            run_debugger(
                ctx=ctx,
                app=app,
                args=list(robot_options_and_args),
                mode=mode,
                addresses=bind,
                port=port if port is not None else DEBUGGER_DEFAULT_PORT,
                pipe_name=pipe_name,
                debug=debug,
                stop_on_entry=stop_on_entry,
                wait_for_client=wait_for_client,
                wait_for_client_timeout=wait_for_client_timeout,
                configuration_done_timeout=configuration_done_timeout,
                debugpy=debugpy,
                debugpy_wait_for_client=debugpy_wait_for_client,
                debugpy_port=debugpy_port,
                output_messages=output_messages,
                output_log=output_log,
                output_timestamps=output_timestamps,
                group_output=group_output,
            )
        )

    except SystemExit:
        raise
    except KeyboardInterrupt:
        app.keyboard_interrupt()
    except Exception as e:
        raise UnknownError(str(e)) from e
