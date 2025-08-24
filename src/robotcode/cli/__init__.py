import json
import logging
import logging.config
from pathlib import Path
from typing import Any, List, Literal, Optional

import click

from robotcode.core.utils.cli import show_hidden_arguments
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.plugin import (
    Application,
    ColoredOutput,
    OutputFormat,
    pass_application,
)
from robotcode.plugin.click_helper.aliases import AliasedGroup
from robotcode.plugin.click_helper.types import EnumChoice
from robotcode.plugin.manager import PluginManager

from .__version__ import __version__
from .commands import config, profiles

old_make_metavar = click.Parameter.make_metavar


def my_make_metavar(self: click.Parameter, *args: Any, **kwargs: Any) -> str:
    metavar = old_make_metavar(self, *args, **kwargs)

    if isinstance(self, click.Option) and self.multiple:
        metavar += " *"

    return metavar


click.Parameter.make_metavar = my_make_metavar  # type: ignore[method-assign]


class RobotCodeFormatter(logging.Formatter):
    def __init__(self, *args: Any, defaults: Any = None, **kwargs: Any) -> None:
        defaults = defaults or {}
        if defaults.get("indent") is None:
            defaults["indent"] = ""
        super().__init__(*args, defaults=defaults, **kwargs)


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
        Config file to use. If not specified, the default config file is used.
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
        The Execution Profile to use. If not specified, the default profile is used.
        """,
)
@click.option(
    "-r",
    "--root",
    "root",
    type=click.Path(exists=True, path_type=Path, dir_okay=True, file_okay=False, resolve_path=True),
    show_envvar=True,
    help="Specifies the root path to be used for the project. It will be automatically detected if not provided.",
)
@click.option(
    "--no-vcs",
    is_flag=True,
    show_envvar=True,
    help="Ignore version control system directories (e.g., .git, .hg) when detecting the project root.",
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
@click.option(
    "-d",
    "--dry",
    is_flag=True,
    show_envvar=True,
    help="Dry run, do not execute any commands.",
)
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
@click.option("--log", is_flag=True, help="Enables logging.", show_envvar=True)
@click.option(
    "--log-level",
    type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Sets the log level.",
    default="CRITICAL",
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--log-format",
    type=str,
    help="Sets the log format. See python logging documentation for more information.",
    default=logging.BASIC_FORMAT,
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--log-style",
    type=click.Choice(["%", "{", "$"]),
    help="Sets the log style. See python logging documentation for more information.",
    default="%",
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--log-filename",
    type=click.Path(
        file_okay=True,
        dir_okay=False,
        writable=True,
        exists=False,
        path_type=str,
    ),
    help="Write log output to a file instead to console.",
    default=None,
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
    "--log-config",
    type=click.Path(
        file_okay=True,
        dir_okay=False,
        readable=True,
        exists=True,
        path_type=str,
    ),
    help="Path to a logging configuration file. This must be a valid Python logging configuration file in JSON format."
    " If this option is set, the other logging options are ignored.",
    default=None,
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--default-path",
    "-dp",
    type=click.Path(exists=False, resolve_path=False, path_type=str),
    multiple=True,
    hidden=show_hidden_arguments(),
    help="Default path to use if no path is given or defined in a profile. "
    "**This is an internal option for running in vscode**",
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
    root: Optional[Path],
    no_vcs: bool,
    format: Optional[OutputFormat],
    dry: bool,
    verbose: bool,
    color: Optional[bool],
    pager: Optional[bool],
    log: bool,
    log_level: str,
    log_format: str,
    log_style: Literal["%", "{", "$"],
    log_filename: Optional[str],
    log_calls: bool,
    log_config: Optional[Path],
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
    app.config.root = root
    app.config.no_vcs = no_vcs

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

    if log_config:
        if log_calls:
            LoggingDescriptor.set_call_tracing(True)

        app.verbose(f"Loading logging configuration from '{log_config}'")
        try:
            with open(log_config, "r", encoding="utf-8") as f:
                config = json.load(f)

            logging.config.dictConfig(config)

        except Exception as e:
            app.error(f"Failed to load logging configuration from '{log_config}': {e}")

    elif log:
        if log_calls:
            LoggingDescriptor.set_call_tracing(True)

        logging.basicConfig(
            level=log_level,
            format=log_format,
            style=log_style,
            filename=log_filename,
        )

        try:
            logging.root.handlers[0].formatter = RobotCodeFormatter(fmt=log_format, style=log_style)
        except TypeError:
            pass

    if debugpy:
        from robotcode.core.utils.debugpy import (
            start_debugpy,
            wait_for_debugpy_connected,
        )

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

for c in PluginManager.instance().cli_commands:
    robotcode.add_command(c)
