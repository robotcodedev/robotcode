import logging
from pathlib import Path
from typing import List, Optional

import click
from robotcode.core.logging import LoggingDescriptor
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
    help="Default path to use if no path is given or defined in a profile. Can be specified multiple times.",
)
@click.option(
    "--launcher-script",
    hidden=True,
    type=str,
    help="Path to the launcher script. This is an internal option.",
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

    if log:
        if log_calls:
            LoggingDescriptor.set_call_tracing(True)

        logging.basicConfig(level=log_level, format="%(name)s:%(levelname)s: %(message)s")


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
