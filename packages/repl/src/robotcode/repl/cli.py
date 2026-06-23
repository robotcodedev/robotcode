import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

from robotcode.plugin import Application, pass_application
from robotcode.plugin._agent_detection import is_running_in_ai_agent
from robotcode.plugin.click_helper.aliases import AliasedCommand
from robotcode.plugin.click_helper.types import add_options
from robotcode.plugin.click_helper.wrappable import wrappable
from robotcode.runner.cli.robot import ROBOT_OPTIONS, ROBOT_VERSION_OPTIONS

from .__version__ import __version__
from ._backends import BACKEND_CHOICES
from ._debug import DebugController, DebugTerminated
from .console_interpreter import _LINE_BREAK_RE, ConsoleInterpreter
from .prompt_toolkit_interpreter import PromptToolkitConsoleInterpreter
from .run import run_repl


def _pick_interpreter(
    *,
    app: Application,
    files: List[Path],
    show_keywords: bool,
    inspect: bool,
    no_history: bool,
    backend: str,
) -> ConsoleInterpreter:
    """Construct the interpreter that matches ``backend``.

    ``plain`` yields `ConsoleInterpreter` (no editor surface). Both
    ``auto`` and ``prompt-toolkit`` yield `PromptToolkitConsoleInterpreter` —
    ``prompt_toolkit`` is a hard runtime dependency, so the two are
    equivalent and ``auto`` exists purely as the user-facing default.
    """
    if backend == "plain":
        return ConsoleInterpreter(
            app=app,
            files=files,
            show_keywords=show_keywords,
            inspect=inspect,
            no_history=no_history,
        )
    if backend not in ("auto", "prompt-toolkit"):
        raise ValueError(f"Unknown backend: {backend!r}. Choose from {BACKEND_CHOICES}.")
    return PromptToolkitConsoleInterpreter(
        app=app,
        files=files,
        show_keywords=show_keywords,
        inspect=inspect,
        no_history=no_history,
    )


def _apply_break_specs(controller: DebugController, specs: Tuple[str, ...]) -> None:
    """Translate `--break` values into controller breakpoints.

    `path:line` becomes a line breakpoint; anything else is a keyword-name
    breakpoint (the RF-natural `--break "Open Browser"`).
    """
    line_breakpoints: Dict[str, List[int]] = {}
    keyword_breakpoints: List[str] = []
    for spec in specs:
        m = _LINE_BREAK_RE.match(spec)
        if m:
            line_breakpoints.setdefault(m.group("path"), []).append(int(m.group("line")))
        else:
            keyword_breakpoints.append(spec)
    for path, lines in line_breakpoints.items():
        controller.set_line_breakpoints(path, lines)
    if keyword_breakpoints:
        controller.set_keyword_breakpoints(keyword_breakpoints)


def _invoke_runner(
    ctx: click.Context,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
) -> None:
    """Run the real suite via the normal `robotcode robot` runner."""
    from robotcode.runner.cli.robot import robot as robot_command

    forwarded: List[str] = []
    for value in by_longname:
        forwarded += ["--by-longname", value]
    for value in exclude_by_longname:
        forwarded += ["--exclude-by-longname", value]
    forwarded += list(robot_options_and_args)

    robot_ctx = robot_command.make_context("robot", forwarded, parent=ctx)
    robot_command.invoke(robot_ctx)


def _is_interactive_stdin() -> bool:
    """Whether stdin is an interactive terminal — drives the `auto` backend choice.

    Wrapped in a helper (rather than calling `sys.stdin.isatty()` inline) so tests
    can simulate a terminal or a pipe without monkeypatching `sys.stdin` itself.
    """
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError, OSError):
        return False


def _resolve_backend(plain: bool, backend: str) -> str:
    """The effective input backend.

    `auto` means *prompt_toolkit on an interactive terminal, plain otherwise*:
    piped/redirected stdin (`echo … | robotcode repl`, heredocs, CI) and
    recognised AI agents can't drive prompt_toolkit's terminal queries, so they
    fall back to the plain `input()` loop that reads until EOF. An explicit
    `--plain` / `--backend` (or `ROBOTCODE_REPL_BACKEND`) always wins.
    """
    if plain and backend not in ("auto", "plain"):
        raise click.UsageError(f"--plain conflicts with --backend={backend}. Use one or the other.")
    if plain:
        backend = "plain"
    if backend == "auto":
        if not _is_interactive_stdin():
            backend = "plain"
        elif (
            not os.environ.get("ROBOTCODE_REPL_PLAIN")
            and not os.environ.get("ROBOTCODE_REPL_BACKEND")
            and is_running_in_ai_agent()
        ):
            backend = "plain"
    return backend


def _resolve_attached(
    debugger_attached: Optional[bool],
    *,
    default: bool,
    has_explicit_triggers: bool,
) -> bool:
    """Resolve the tri-state `--debugger-attached` flag to a concrete state.

    An explicit `--debugger-attached` / `--no-debugger-attached` always wins.
    Otherwise the debugger attaches when an explicit pause trigger was given
    (so `repl --break …` just works), falling back to `default`."""
    if debugger_attached is not None:
        return debugger_attached
    if has_explicit_triggers:
        return True
    return default


def _attach_debugger(
    interpreter: ConsoleInterpreter,
    *,
    break_at: Tuple[str, ...],
    attached: bool = True,
    stop_on_entry: bool = False,
    break_on_exception: bool = True,
    break_on_all_exceptions: bool = False,
    break_on_failed_test: bool = False,
    break_on_failed_suite: bool = False,
) -> DebugController:
    """Wire a `DebugController` onto `interpreter` and apply the pause triggers.

    The interpreter *is* the debug front-end: its logger feeds the controller,
    and a pause drops into its own prompt (`wait_at_stop`) with the full
    dot-command set — session commands and debugger commands together.

    The controller is always wired and its breakpoints/exception filters are
    always armed; `attached` only decides whether it actively pauses. A detached
    debugger keeps its configuration, so `.debug on` resumes with the same
    triggers."""
    controller = DebugController()
    controller.set_frontend(interpreter)
    interpreter.set_controller(controller)
    interpreter.register_observer(controller)
    if stop_on_entry:
        controller.set_stop_on_entry(True)
    # Exception breakpoints — `uncaught` is on by default; the rest opt-in.
    # (Each is toggleable at runtime via `.catch`.)
    exception_filters: List[str] = []
    if break_on_exception:
        exception_filters.append("uncaught_failed_keyword")
    if break_on_all_exceptions:
        exception_filters.append("failed_keyword")
    if break_on_failed_test:
        exception_filters.append("failed_test")
    if break_on_failed_suite:
        exception_filters.append("failed_suite")
    if exception_filters:
        controller.set_exception_breakpoints(exception_filters)
    _apply_break_specs(controller, break_at)
    controller.set_attached(attached)
    return controller


# Shared base options — the REPL/prompt-frontend behaviour. Conflict-free with
# `ROBOT_OPTIONS` (which has no such options), so they can sit on both `repl`
# and `robot-debug` without duplicate-option clashes.
REPL_BASE_OPTIONS = [
    click.option(
        "--no-history",
        is_flag=True,
        default=False,
        envvar="ROBOTCODE_REPL_NO_HISTORY",
        help="Don't load or save the persistent history file. In-session "
        "arrow-up recall still works, but nothing crosses session boundaries. "
        "Useful for AI-agent invocations or quick spike sessions you don't "
        "want polluting your shell's REPL history.",
    ),
    click.option(
        "--backend",
        type=click.Choice(list(BACKEND_CHOICES)),
        default="auto",
        show_default=True,
        envvar="ROBOTCODE_REPL_BACKEND",
        help="Force a specific input backend instead of auto-picking. "
        "`auto` and `prompt-toolkit` both pick the prompt-toolkit-driven "
        "interpreter (completion, syntax highlighting, history, doc viewer). "
        "`plain` drops to a bare `input()` prompt — useful when ANSI escapes "
        "or popups would interfere with the surrounding capture.",
    ),
    click.option(
        "--plain",
        is_flag=True,
        default=False,
        envvar="ROBOTCODE_REPL_PLAIN",
        help="Shorthand for `--backend=plain`. Disables all prompt enhancements — "
        "completion, syntax highlighting, candidate popup, auto-suggest, history "
        "file. The prompt becomes a bare `input()` call. Recommended for "
        "AI-agent invocations, automation pipelines, and any context where ANSI "
        "escapes or completion popups would interfere with stdin/stdout capture. "
        "Conflicts with `--backend=<other>`.",
    ),
]

# `repl`-only options (interactive session setup + snippet files).
SHELL_OPTIONS = [
    click.option(
        "-v",
        "--variable",
        metavar="name:value",
        type=str,
        multiple=True,
        help="Set variables in the test data. See `robot --variable` option.",
    ),
    click.option(
        "-V",
        "--variablefile",
        metavar="PATH",
        type=str,
        multiple=True,
        help="Python or YAML file to read variables from. See `robot --variablefile` option.",
    ),
    click.option(
        "-P",
        "--pythonpath",
        metavar="PATH",
        type=str,
        multiple=True,
        help="Additional locations where to search test libraries"
        " and other extensions when they are imported. See `robot --pythonpath` option.",
    ),
    click.option(
        "-k",
        "--show-keywords",
        is_flag=True,
        default=False,
        help="Executed keywords will be shown in the output.",
    ),
    click.option(
        "-i",
        "--inspect",
        is_flag=True,
        default=False,
        help="Activate inspection mode. This forces a prompt to appear after the REPL script is executed.",
    ),
    click.option(
        "-d",
        "--outputdir",
        metavar="DIR",
        type=str,
        help="Where to create output files. See `robot --outputdir` option.",
    ),
    click.option(
        "-o",
        "--output",
        metavar="FILE",
        type=str,
        help="XML output file. See `robot --output` option.",
    ),
    click.option(
        "-r",
        "--report",
        metavar="FILE",
        type=str,
        help="HTML output file. See `robot --report` option.",
    ),
    click.option(
        "-l",
        "--log",
        metavar="FILE",
        type=str,
        help="HTML log file. See `robot --log` option.",
    ),
    click.option(
        "-x",
        "--xunit",
        metavar="FILE",
        type=str,
        help="xUnit output file. See `robot --xunit` option.",
    ),
    click.option(
        "-s",
        "--source",
        type=click.Path(path_type=Path),
        metavar="FILE",
        help="Use the parent directory of FILE as the REPL's working directory. "
        "Relative paths inside `Import Resource`, `Import Library`, "
        "file-based variables, etc. resolve against that directory. "
        "The file itself is never read or written, so the path doesn't "
        "need to exist.",
    ),
    click.argument(
        "files",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        nargs=-1,
        required=False,
    ),
]

# Debugger options — shared by `repl` and `robot-debug`. `--debugger-attached`
# is the master switch (does anything pause at all?); the `--break*` flags are
# the individual pause triggers. (`robot-debug` adds `--stop-on-entry`, which
# has no meaning for the interactive shell.)
DEBUG_OPTIONS = [
    click.option(
        "--debugger-attached/--no-debugger-attached",
        default=None,
        help="Whether the debugger is active. While detached nothing pauses — a "
        "failing keyword just prints its error and you stay at the prompt — but "
        "breakpoints and exception filters stay configured. Default: attached "
        "for `robot-debug`; for `repl` detached, unless a pause trigger "
        "(`--break`, a `--break-on-*` flag) is given. Toggle at runtime with "
        "`.debug on` / `.debug off`.",
    ),
    click.option(
        "--break",
        "break_at",
        metavar="LOCATION",
        multiple=True,
        help="Break at LOCATION — a `file:line` or a keyword name. Repeatable.",
    ),
    click.option(
        "--break-on-exception/--no-break-on-exception",
        default=None,
        help="Break at an uncaught failing keyword (not caught by TRY/EXCEPT or "
        "`Run Keyword And …`), before the failure unwinds. Armed by default; it "
        "only pauses while the debugger is attached (see `--debugger-attached`).",
    ),
    click.option(
        "--break-on-all-exceptions/--no-break-on-all-exceptions",
        default=False,
        show_default=True,
        help="Break at EVERY failing keyword, even ones caught by TRY/EXCEPT or `Run Keyword And …`.",
    ),
    click.option(
        "--break-on-failed-test/--no-break-on-failed-test",
        default=False,
        show_default=True,
        help="Break at the end of a failing test.",
    ),
    click.option(
        "--break-on-failed-suite/--no-break-on-failed-suite",
        default=False,
        show_default=True,
        help="Break at the end of a failing suite.",
    ),
]


@wrappable
@click.command(cls=AliasedCommand, aliases=["shell"], add_help_option=True)
@add_options(*REPL_BASE_OPTIONS)
@add_options(*SHELL_OPTIONS)
@add_options(*DEBUG_OPTIONS)
@click.version_option(version=__version__, prog_name="RobotCode REPL")
@pass_application
def repl(
    app: Application,
    variable: Tuple[str, ...],
    variablefile: Tuple[str, ...],
    pythonpath: Tuple[str, ...],
    show_keywords: bool,
    inspect: bool,
    no_history: bool,
    backend: str,
    plain: bool,
    outputdir: Optional[str],
    output: Optional[str],
    report: Optional[str],
    log: Optional[str],
    xunit: Optional[str],
    source: Optional[Path],
    files: Tuple[Path, ...],
    debugger_attached: Optional[bool],
    break_at: Tuple[str, ...],
    break_on_exception: Optional[bool],
    break_on_all_exceptions: bool,
    break_on_failed_test: bool,
    break_on_failed_suite: bool,
) -> None:
    """Run Robot Framework interactively (alias `shell`).

    Starts an interactive session where you enter Robot Framework keywords and
    run them immediately. Pass FILES to execute them in the session.
    """
    if files:
        files = tuple(f.absolute() for f in files)

    # The shell starts with the debugger *detached* — a failing keyword prints
    # its error and you stay at the prompt — unless a pause trigger was given
    # (then attach so `--break …` just works) or `--debugger-attached` forces it.
    # `.debug on` / `.debug off` toggles it at runtime. Exception breaking is
    # armed by default; it only fires while attached.
    has_explicit_triggers = (
        bool(break_at)
        or break_on_exception is True
        or (break_on_all_exceptions or break_on_failed_test or break_on_failed_suite)
    )
    attached = _resolve_attached(debugger_attached, default=False, has_explicit_triggers=has_explicit_triggers)

    backend = _resolve_backend(plain, backend)

    interpreter = _pick_interpreter(
        app=app,
        files=list(files),
        show_keywords=show_keywords,
        inspect=inspect,
        no_history=no_history,
        backend=backend,
    )
    # The debugger stays wired for the whole interactive session and is torn down
    # with the interpreter when the session ends — so, unlike `robot`, there is no
    # per-run unregister here. `attached` decides whether it actually pauses.
    _attach_debugger(
        interpreter,
        break_at=break_at,
        attached=attached,
        break_on_exception=break_on_exception is not False,
        break_on_all_exceptions=break_on_all_exceptions,
        break_on_failed_test=break_on_failed_test,
        break_on_failed_suite=break_on_failed_suite,
    )

    run_repl(
        interpreter=interpreter,
        app=app,
        variable=variable,
        variablefile=variablefile,
        pythonpath=pythonpath,
        outputdir=outputdir,
        output=output,
        report=report,
        log=log,
        xunit=xunit,
        source=source,
        files=files,
    )


@wrappable
@click.command(
    cls=AliasedCommand,
    aliases=["run-debug"],
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    add_help_option=True,
    epilog="Use `-- --help` to see `robot` help.",
)
@add_options(*REPL_BASE_OPTIONS)
@add_options(*(ROBOT_OPTIONS - ROBOT_VERSION_OPTIONS))
@add_options(*DEBUG_OPTIONS)
@click.option(
    "--stop-on-entry",
    is_flag=True,
    default=False,
    help="Break at the very first keyword.",
)
@add_options(*ROBOT_VERSION_OPTIONS)
@pass_application
@click.pass_context
def robot_debug(
    ctx: click.Context,
    app: Application,
    by_longname: Tuple[str, ...],
    exclude_by_longname: Tuple[str, ...],
    robot_options_and_args: Tuple[str, ...],
    no_history: bool,
    backend: str,
    plain: bool,
    debugger_attached: Optional[bool],
    break_at: Tuple[str, ...],
    stop_on_entry: bool,
    break_on_exception: Optional[bool],
    break_on_all_exceptions: bool,
    break_on_failed_test: bool,
    break_on_failed_suite: bool,
) -> None:
    """Run a real Robot Framework suite with the debugger attached (alias `run-debug`).

    Takes the same arguments as `robotcode robot`, but pauses at breakpoints so
    you can inspect and step through the run at a debug prompt.
    """
    # Debugging a real run: the debugger is attached by default (the point of the
    # command), breaking on the first uncaught failure unless turned off. Only an
    # explicit `--no-debugger-attached` detaches it (then it runs like `robot`).
    attached = _resolve_attached(debugger_attached, default=True, has_explicit_triggers=False)

    backend = _resolve_backend(plain, backend)

    interpreter = _pick_interpreter(
        app=app, files=[], show_keywords=False, inspect=False, no_history=no_history, backend=backend
    )
    controller = _attach_debugger(
        interpreter,
        break_at=break_at,
        attached=attached,
        stop_on_entry=stop_on_entry,
        break_on_exception=break_on_exception is not False,
        break_on_all_exceptions=break_on_all_exceptions,
        break_on_failed_test=break_on_failed_test,
        break_on_failed_suite=break_on_failed_suite,
    )

    # `robot-debug` produces the same console output as `robotcode robot` — the run
    # is fully visible. At a stop the debug prompt is interleaved with Robot's live
    # console; `_render_stop` breaks off any in-progress status line, and the run's
    # output resumes on continue/step/detach. The console mode is left to Robot's
    # default (or the user's `--console`), not forced.
    try:
        with interpreter.forward_events(echo_messages=False):
            _invoke_runner(ctx, by_longname, exclude_by_longname, robot_options_and_args)
    except DebugTerminated:
        app.echo("Debugger: run terminated.")
    finally:
        interpreter.unregister_observer(controller)
