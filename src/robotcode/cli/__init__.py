import json
import logging
import logging.config
import os
from pathlib import Path
from typing import IO, Any, List, Literal, Mapping, Optional

import click

from robotcode.core.utils.cli import show_hidden_arguments
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.plugin import (
    Application,
    ColoredOutput,
    OutputFormat,
    pass_application,
    show_error,
)
from robotcode.plugin._agent_detection import is_running_in_ai_agent
from robotcode.plugin.click_helper.aliases import AliasedGroup
from robotcode.plugin.click_helper.exit_codes import has_robot_exit_codes
from robotcode.plugin.click_helper.types import EnumChoice
from robotcode.plugin.click_helper.wrappable import WRAPPER_APPLIED_ENV, invoked_command_is_wrappable, is_wrappable
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


def _warn_about_ignored_wrapper(ctx: click.Context, app: Application) -> None:
    """Warn about a ``--wrapper`` that does not apply.

    The command itself starts robotcode under the ``wrapper``, once it has loaded its
    configuration (see `robotcode.plugin.click_helper.wrappable.run_under_wrapper`).
    """
    if app.config.no_wrapper:
        if app.config.wrapper:
            app.warning("Ignoring --wrapper because --no-wrapper was given.")
        return
    if not app.config.wrapper or os.environ.get(WRAPPER_APPLIED_ENV) or not ctx.invoked_subcommand:
        return
    if not invoked_command_is_wrappable(ctx):
        app.warning(f"Ignoring --wrapper: '{ctx.invoked_subcommand}' does not execute Robot Framework.")


def _set_output_options(app: Application, color: Optional[bool], pager: Optional[bool]) -> None:
    """Set the colour and pager choice of `app` from `--color/--no-color` and `--pager/--no-pager`."""
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


def _application_for(params: Mapping[str, Any]) -> Application:
    """An `Application` for an error that comes before the root command has set one up,
    set up from robotcode's own options `params` as far as they are known."""
    app = Application()
    _set_output_options(app, params.get("color"), params.get("pager"))
    return app


class RobotCodeError(click.ClickException):
    """An error that stops a robotcode command, written as robotcode writes the errors it
    reports (`robotcode.plugin.show_error`). Keeps the exit code of the error."""

    def __init__(self, error: click.ClickException, app: Application) -> None:
        super().__init__(error.message)
        self.error = error
        self.app = app
        # click declares the exit code on the class; this one is the code of the error
        self.exit_code = error.exit_code  # type: ignore[misc]

    def show(self, file: Optional[IO[Any]] = None) -> None:
        show_error(self.app, self.error, file)


class RobotDataError(RobotCodeError):
    """An error robotcode reports itself for a command that passes on Robot Framework's
    exit codes.

    Exits with Robot Framework's code for invalid data or command line options instead of
    Click's 1 or 2.
    """

    def __init__(self, error: click.ClickException, app: Application) -> None:
        super().__init__(error, app)
        self.exit_code = 252  # type: ignore[misc]


class RobotCodeGroup(AliasedGroup):
    """The root command group.

    Commands that run Robot Framework (`wrappable`) or pass on the exit code of a Robot
    Framework tool (`robot_exit_codes`) answer with its exit codes, where 1-250 counts the
    failed tests. An error robotcode reports itself for such a command - a Click error with
    exit code 1 or 2, such as a broken configuration, a wrapper that doesn't start or an
    invalid option - exits with Robot Framework's 252 instead. Robot Framework's own exit
    codes never arrive as Click errors, so they pass through unchanged, and so does any
    other code.

    Every Click error of a command or of the group's own options is written as
    `[ ERROR ] <message>`, with the `Application` of the command. An error that comes
    before the root command has set it up - a command name that does not exist or is
    missing, an invalid option of robotcode itself - gets one set up from robotcode's own
    options, so that `--no-color` and AI-agent sessions apply to it too.
    """

    def make_context(
        self, info_name: Optional[str], args: List[str], parent: Optional[click.Context] = None, **extra: Any
    ) -> click.Context:
        # Click's parser takes the arguments out of the list it gets
        command_line = list(args)
        try:
            return super().make_context(info_name, args, parent, **extra)
        except click.ClickException as e:
            # Click stops at an invalid option before it takes any value; read robotcode's
            # own options again as Click's shell completion does, without errors or
            # callbacks, passing over unknown options
            lenient = {**extra, "resilient_parsing": True, "ignore_unknown_options": True}
            try:
                params = super().make_context(info_name, command_line, parent, **lenient).params
            except click.ClickException:
                params = {}
            raise RobotCodeError(e, _application_for(params)) from e

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except click.ClickException as e:
            app = ctx.find_object(Application) or _application_for(ctx.params)
            if e.exit_code in (1, 2) and self._passes_on_robot_exit_codes(ctx):
                raise RobotDataError(e, app) from e
            raise RobotCodeError(e, app) from e

    def _passes_on_robot_exit_codes(self, ctx: click.Context) -> bool:
        name = ctx.invoked_subcommand
        cmd = self.get_command(ctx, name) if name else None
        return cmd is not None and (is_wrappable(cmd) or has_robot_exit_codes(cmd))


@click.group(
    cls=RobotCodeGroup,
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
        "Enable or disable colored output. Color codes are written only to a terminal; set `FORCE_COLOR` to get"
        " them in a pipe. Default (no flag): auto-detect — colors only when stdout is a TTY, disabled if `NO_COLOR`"
        " is set, forced if `FORCE_COLOR` is set."
    ),
    show_envvar=True,
)
@click.option(
    "--pager / --no-pager",
    "pager",
    default=None,
    help=(
        "Force or disable the pager on a terminal; no pager starts when stdout isn't a TTY. Default (no flag):"
        " auto-page when the rendered output exceeds the terminal height."
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

    _set_output_options(app, color, pager)
    app.config.output_format = format
    app.config.launcher_script = launcher_script
    app.config.default_paths = default_path
    app.config.log_enabled = log
    app.config.log_level = log_level
    app.config.log_calls = log_calls
    app.config.wrapper = wrapper
    app.config.no_wrapper = no_wrapper

    _warn_about_ignored_wrapper(ctx, app)

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
