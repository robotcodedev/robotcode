import logging
from pathlib import Path
from typing import List, Optional

import click
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.utils.cli import show_hidden_arguments
from robotcode.plugin import Application, ColoredOutput, OutputFormat, pass_application
from robotcode.plugin.click_helper.aliases import AliasedGroup
from robotcode.plugin.click_helper.types import EnumChoice
from robotcode.plugin.manager import PluginManager

from .__version__ import __version__
from .commands import config, profiles


@click.group(
    cls=AliasedGroup,
    context_settings={"auto_envvar_prefix": "ROBOTCODE"},
    invoke_without_command=False,
)
@click.option(
    "-c",
    "--config",
    "config_files",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    show_envvar=True,
    help="""\
        Config file to use. Can be specified multiple times.
        If not specified, the default config file is used.
        """,
)
@click.option(
    "-p",
    "--profile",
    "profiles",
    type=str,
    multiple=True,
    show_envvar=True,
    help="""\
        The Execution Profile to use. Can be specified multiple times.
        If not specified, the default profile is used.
        """,
)
@click.option(
    "-f",
    "--format",
    "format",
    type=EnumChoice(OutputFormat),
    default=None,
    help="Set the output format.",
    show_default=True,
)
@click.option("-d", "--dry", is_flag=True, show_envvar=True, help="Dry run, do not execute any commands.")
@click.option(
    "--color / --no-color",
    "color",
    default=None,
    help="Whether or not to display colored output (default is auto-detection).",
    show_envvar=True,
)
@click.option(
    "--pager / --no-pager",
    "pager",
    default=False,
    help="Whether or not use a pager to display long text or data.",
    show_envvar=True,
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enables verbose mode.",
    show_envvar=True,
)
@click.option(
    "--log",
    is_flag=True,
    help="Enables logging.",
    show_envvar=True,
)
@click.option(
    "--log-level",
    type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Sets the log level.",
    default="CRITICAL",
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--log-calls",
    is_flag=True,
    help="Enables logging of method/function calls.",
    show_envvar=True,
)
@click.option(
    "--default-path",
    "-dp",
    type=click.Path(exists=False, resolve_path=False, path_type=str),
    multiple=True,
    hidden=show_hidden_arguments(),
    help="Default path to use if no path is given or defined in a profile. Can be specified multiple times. "
    "**This is an internal option for running in vscode",
)
@click.option(
    "--launcher-script",
    hidden=show_hidden_arguments(),
    type=str,
    help="Path to the launcher script. This is an internal option.",
)
@click.option(
    "--debugpy",
    is_flag=True,
    hidden=show_hidden_arguments(),
    show_envvar=True,
    help="Starts a debugpy session. "
    "**This is an internal option and should only be use if you want to debug _RobotCode_.**",
)
@click.option(
    "--debugpy-port",
    type=int,
    default=5678,
    show_default=True,
    show_envvar=True,
    hidden=show_hidden_arguments(),
    help="Defines the port to use for the debugpy session.",
)
@click.option(
    "--debugpy-wait-for-client",
    is_flag=True,
    hidden=show_hidden_arguments(),
    show_envvar=True,
    help="Waits for a debugpy client to connect before starting the debugpy session.",
)
@click.version_option(version=__version__, prog_name="robotcode")
@pass_application
def robotcode(
    app: Application,
    config_files: Optional[List[Path]],
    profiles: Optional[List[str]],
    format: Optional[OutputFormat],
    dry: bool,
    verbose: bool,
    color: Optional[bool],
    pager: Optional[bool],
    log: bool,
    log_level: str,
    log_calls: bool,
    default_path: Optional[List[str]],
    launcher_script: Optional[str] = None,
    debugpy: bool = False,
    debugpy_port: int = 5678,
    debugpy_wait_for_client: bool = False,
) -> None:
    """\b
     _____       _           _    _____          _
    |  __ \\     | |         | |  / ____|        | |
    | |__) |___ | |__   ___ | |_| |     ___   __| | ___
    |  _  // _ \\| '_ \\ / _ \\| __| |    / _ \\ / _  |/ _ \\
    | | \\ \\ (_) | |_) | (_) | |_| |___| (_) | (_| |  __/
    |_|  \\_\\___/|_.__/ \\___/ \\__|\\_____\\___/ \\__,_|\\___|
    A CLI tool for Robot Framework.

    """
    app.config.config_files = config_files
    app.config.profiles = profiles
    app.config.dry = dry
    app.config.verbose = verbose

    if color is None:
        app.config.colored_output = ColoredOutput.AUTO
    elif color:
        app.config.colored_output = ColoredOutput.YES
    else:
        app.config.colored_output = ColoredOutput.NO
    app.config.pager = pager
    app.config.output_format = format
    app.config.launcher_script = launcher_script
    app.config.default_paths = default_path
    app.config.log_enabled = log
    app.config.log_level = log_level
    app.config.log_calls = log_calls

    if log:
        if log_calls:
            LoggingDescriptor.set_call_tracing(True)

        logging.basicConfig(level=log_level, format="%(name)s:%(levelname)s: %(message)s")

    if debugpy:
        from robotcode.core.utils.debugpy import start_debugpy, wait_for_debugpy_connected

        app.verbose(f"Try to start a debugpy session on port {debugpy_port}")

        real_port = start_debugpy(debugpy_port, False)

        if real_port is not None:
            if real_port != debugpy_port:
                app.verbose(f"Debugpy session started on port {real_port}")

            if debugpy_wait_for_client:
                app.verbose("Waiting for debugpy client to connect...")
                wait_for_debugpy_connected()

            app.verbose("Debugpy session started")
        else:
            app.verbose("Could not start debugpy session. Enable logging for more information.")


robotcode.add_command(config)
robotcode.add_command(profiles)

for p in PluginManager().cli_commands:
    for c in p:
        robotcode.add_command(c)


@robotcode.command()
@click.pass_context
def clean(ctx: click.Context) -> None:
    """TODO: Cleans a Robot Framework project.

    TODO: This is not implemented yet.
    """
    click.echo("TODO")


@robotcode.command()
@click.pass_context
def new(ctx: click.Context) -> None:
    """TODO: Create a new Robot Framework project.

    TODO: This is not implemented yet.
    """
    click.echo("TODO")
