import json
import logging
import logging.config
import os
import shlex
import sys
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
from robotcode.plugin._agent_detection import is_running_in_ai_agent
from robotcode.plugin.click_helper.aliases import AliasedGroup
from robotcode.plugin.click_helper.types import EnumChoice
from robotcode.plugin.click_helper.wrappable import WRAPPER_APPLIED_ENV, is_wrappable
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


def _maybe_reexec_under_wrapper(
    ctx: click.Context, app: Application, cli_wrapper: Optional[str] = None, no_wrapper: bool = False
) -> None:
    """Re-execute this process through a configured ``wrapper`` command.

    When a ``wrapper`` is configured - either via ``--wrapper`` on the command
    line (``cli_wrapper``) or the selected profile's ``wrapper`` (e.g. to run
    the tests inside a specific X11/Wayland session) - and the invoked command
    is ``@wrappable`` (i.e. it executes Robot Framework), the process
    re-executes itself **once** through that command before Robot Framework
    starts. ``--wrapper`` overrides the profile; ``--no-wrapper`` disables
    wrapping for this run. The guard env var prevents infinite recursion and
    lets an outer layer suppress the re-exec by setting it itself.
    """
    if no_wrapper:
        if cli_wrapper:
            app.warning("Ignoring --wrapper because --no-wrapper was given.")
        return
    if os.environ.get(WRAPPER_APPLIED_ENV):
        return

    sub_name = ctx.invoked_subcommand
    if not sub_name:
        return
    # The command itself opts in via @wrappable; aliases resolve to the same
    # command object, so this is alias-safe and needs no central name list.
    sub_cmd = ctx.command.get_command(ctx, sub_name) if isinstance(ctx.command, click.Group) else None
    if sub_cmd is None or not is_wrappable(sub_cmd):
        if cli_wrapper:
            app.warning(f"Ignoring --wrapper: '{sub_name}' does not execute Robot Framework.")
        return

    from robotcode.robot.config.loader import load_robot_config_from_path
    from robotcode.robot.config.utils import get_config_files

    profile_wrapper = None
    try:
        config_files, _, _ = get_config_files(
            config_files=app.config.config_files,
            root_folder=app.config.root,
            no_vcs=app.config.no_vcs,
            verbose_callback=app.verbose,
        )
        # `evaluated_with_env` also applies the profile's `env` to `os.environ`,
        # so the wrapper command can rely on it.
        profile = (
            load_robot_config_from_path(*config_files, verbose_callback=app.verbose)
            .combine_profiles(*(app.config.profiles or []), verbose_callback=app.verbose, error_callback=app.error)
            .evaluated_with_env(verbose_callback=app.verbose, error_callback=app.error)
        )
        profile_wrapper = profile.wrapper
    except Exception as e:
        # Don't fail early on config problems here; the actual command loads the
        # config again and reports errors properly. An explicit --wrapper is
        # still honored below.
        message = str(e)
        app.verbose(lambda: f"Skipping profile wrapper detection: {message}")

    # `--wrapper` overrides the profile's `wrapper`. The evaluated profile turns
    # StringExpression entries into plain strings.
    if cli_wrapper:
        wrapper = shlex.split(cli_wrapper)
    elif profile_wrapper:
        wrapper = [str(w) for w in profile_wrapper]
    else:
        return

    command = [*wrapper, sys.executable, "-m", "robotcode.cli", *sys.argv[1:]]
    app.verbose(lambda: "Re-executing under wrapper: " + " ".join(command))

    os.environ[WRAPPER_APPLIED_ENV] = "1"
    try:
        os.execvp(command[0], command)
    except OSError as e:
        raise click.ClickException(f"Failed to execute wrapper command {wrapper!r}: {e}") from e


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
    help=(
        "Force or disable colored output. Default (no flag): auto-detect — colors only when stdout is a TTY,"
        " disabled if `NO_COLOR` is set, forced if `FORCE_COLOR` is set."
    ),
    show_envvar=True,
)
@click.option(
    "--pager / --no-pager",
    "pager",
    default=None,
    help=(
        "Force or disable the pager. Default (no flag): auto-page when the rendered output exceeds the terminal height."
    ),
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
    "--wrapper",
    type=str,
    default=None,
    show_envvar=True,
    help='Command prefix to run the test execution through, e.g. `--wrapper "xvfb-run -a"`. '
    "Split like a shell command. Applies only to commands that execute Robot Framework "
    "(run/debug/repl). Overrides the profile's `wrapper`.",
)
@click.option(
    "--no-wrapper",
    is_flag=True,
    help="Disable any configured `wrapper` (profile or --wrapper) for this run.",
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
@click.pass_context
def robotcode(
    ctx: click.Context,
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
    wrapper: Optional[str] = None,
    no_wrapper: bool = False,
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

    # AI-agent auto-detect: when running inside a known agent session
    # (Claude Code, Copilot, OpenCode, …) demote colour and pager
    # defaults so the agent's stdout capture stays clean. Explicit CLI
    # flags and `NO_COLOR` / `FORCE_COLOR` keep their precedence.
    if is_running_in_ai_agent():
        if color is None and not os.environ.get("NO_COLOR") and not os.environ.get("FORCE_COLOR"):
            app.config.colored_output = ColoredOutput.NO
        if pager is None:
            app.config.pager = False
    app.config.output_format = format
    app.config.launcher_script = launcher_script
    app.config.default_paths = default_path
    app.config.log_enabled = log
    app.config.log_level = log_level
    app.config.log_calls = log_calls

    _maybe_reexec_under_wrapper(ctx, app, wrapper, no_wrapper)

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
