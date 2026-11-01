import dataclasses
import multiprocessing
import os
import sys
import time
from typing import Any, Callable, List, Optional, Tuple, Type, TypeVar

import click
from click.core import ParameterSource
from robot.errors import DATA_ERROR

from robotcode.core.utils.dataclasses import as_dict
from robotcode.core.utils.path import same_file
from robotcode.plugin import Application, OutputFormat, pass_application
from robotcode.plugin.click_helper.exit_codes import robot_exit_codes
from robotcode.plugin.click_helper.types import add_options

from ._session import (
    STARTUP_LIMIT,
    AnswerStatus,
    ChannelAnswer,
    MovedAnswer,
    OutputAnswer,
    RefusedAnswer,
    Request,
    RestartedAnswer,
    RestartFailedAnswer,
    ResultAnswer,
    SessionAnswer,
    SessionEntry,
    SessionKind,
    SessionRequest,
    StateAnswer,
    StoppedAnswer,
    connect,
    create_output_pipe,
    create_sessions_dir,
    new_session_id,
    open_sessions,
    project_folder,
    read_entry,
    read_to_end,
    remove_session_files,
    sessions_dir,
    start_session_process,
)

if sys.platform == "win32":
    import msvcrt

F = TypeVar("F", bound=Callable[..., Any])
A = TypeVar("A", bound=SessionAnswer)

# How long `session start` waits for a session to take commands, when `--timeout` isn't longer.
_STARTUP_LIMIT = STARTUP_LIMIT

# 124 for a statement that still runs, as `timeout(1)` exits.
_EXIT_CODES = {AnswerStatus.PASSED: 0, AnswerStatus.FAILED: 1, AnswerStatus.RUNNING: 124}


def _timeout_option(what: str) -> Callable[[F], F]:
    return click.option(
        "--timeout",
        type=click.FloatRange(min=0),
        default=60,
        show_default=True,
        metavar="SECONDS",
        help=f"Wait at most SECONDS for {what}. After that, print the output so far and exit with code 124, while "
        "the session goes on; `session wait` prints the rest.",
    )


@click.group(invoke_without_command=False)
def session() -> None:
    """\
    Run a REPL or a debug run in the background and give it one input after the other.

    `session start` starts the session and prints its ID, which the other commands
    take. The session keeps running when the command has returned, until it is
    stopped or has waited for the idle timeout without a request. When the REPL
    exits or the debug run ends, the session stays open: `session status` tells
    it, `session result` prints the exit code, and `session restart` starts it
    again.

    \b
    Examples:
    ```
    robotcode session start repl
    robotcode session send repl-3f9a2c1e "Evaluate    1 + 1"
    robotcode session start debug --break tests/orders.robot:19 tests
    robotcode session send debug-7b2d9e04 ".vars --user"
    robotcode session stop repl-3f9a2c1e
    ```
    """


# Errors of robotcode itself exit with 252, as other commands that run Robot Framework do, and not with the 1 of an
# input that failed.
robot_exit_codes(session)


@session.group(invoke_without_command=False)
def start() -> None:
    """\
    Start a session in the background and print its ID and its output up to its first prompt or its end.

    `start` returns once the session takes commands. A session that isn't
    ready within 60 seconds, or within `--timeout` when that is longer, is
    ended.
    """


_START_OPTIONS = [
    click.option(
        "--idle-timeout",
        type=click.FloatRange(min=0, min_open=True),
        default=15,
        show_default=True,
        metavar="MINUTES",
        help="End the session when it has waited at its prompt for MINUTES without a request. A statement that "
        "runs doesn't count as waiting.",
    ),
    _timeout_option("the first prompt"),
    click.argument("args", nargs=-1, type=click.UNPROCESSED),
]


@start.command(
    name="repl",
    context_settings={"ignore_unknown_options": True},
    epilog="Takes the options and arguments of `robotcode repl`.",
)
@add_options(*_START_OPTIONS)
@pass_application
@click.pass_context
def start_repl(
    ctx: click.Context, app: Application, idle_timeout: float, timeout: float, args: Tuple[str, ...]
) -> None:
    """Start `robotcode repl` in the background; the session is ready at its first prompt."""
    _start(ctx, app, SessionKind.REPL, idle_timeout, timeout, args)


@start.command(
    name="debug",
    context_settings={"ignore_unknown_options": True},
    epilog="Takes the options and arguments of `robotcode robot-debug`.",
)
@add_options(*_START_OPTIONS)
@pass_application
@click.pass_context
def start_debug(
    ctx: click.Context, app: Application, idle_timeout: float, timeout: float, args: Tuple[str, ...]
) -> None:
    """Start `robotcode robot-debug` in the background; the session is ready at its first stop or at the end of the
    run."""
    _start(ctx, app, SessionKind.DEBUG, idle_timeout, timeout, args)


def _robotcode_options(ctx: click.Context) -> List[str]:
    """The options given to `robotcode` itself on the command line, which the session process gets too; options from
    the environment reach it with the environment."""
    root = ctx.find_root()
    args: List[str] = []
    for param in root.command.params:
        if not isinstance(param, click.Option) or param.name is None or param.name not in root.params:
            continue
        if root.get_parameter_source(param.name) is not ParameterSource.COMMANDLINE:
            continue
        value = root.params[param.name]
        if param.is_flag:
            if value:
                args.append(param.opts[0])
            elif param.secondary_opts:
                args.append(param.secondary_opts[0])
        elif param.multiple:
            for item in value:
                args += [param.opts[0], str(item)]
        elif value is not None:
            args += [param.opts[0], str(value)]
    return args


def _start(
    ctx: click.Context, app: Application, kind: SessionKind, idle_timeout: float, timeout: float, args: Tuple[str, ...]
) -> None:
    session_id = new_session_id(kind)
    try:
        create_sessions_dir()
    except OSError as e:
        # A sandbox, for example, can keep a command from writing there.
        raise click.ClickException(
            f"Can't create the files of the session in {sessions_dir()}: {e.strerror or e}."
        ) from e
    # The process writes its standard output and standard error to the pipe and reads it at the other end.
    read_end, write_end = create_output_pipe()
    if sys.platform == "win32":
        output = msvcrt.get_osfhandle(read_end)
    else:
        output = read_end
    command = [
        sys.executable,
        "-m",
        "robotcode.cli",
        *_robotcode_options(ctx),
        "--no-color",
        "--no-pager",
        kind.command,
        "--serve-session",
        session_id,
        "--serve-output",
        str(output),
        "--serve-idle-timeout",
        str(idle_timeout),
        *args,
    ]
    # Unbuffered, so that an answer has all the output written before it, and in UTF-8, which the session decodes.
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        process = start_session_process(command, output, write_end, env)
    finally:
        os.close(write_end)

    try:
        # `--timeout` is for the first prompt. Until the session takes commands at all, `start` waits longer, so that
        # the other commands always reach a session whose ID it has printed.
        deadline = time.monotonic() + timeout
        limit = max(timeout, _STARTUP_LIMIT)
        ready_by = time.monotonic() + limit
        entry = read_entry(session_id)
        while entry is None:
            if process.poll() is not None:
                _ended_before_ready(
                    app,
                    session_id,
                    read_to_end(read_end),
                    f"The session ended before it was ready, with exit code {process.returncode}.",
                    process.returncode,
                )
            if time.monotonic() >= ready_by:
                process.kill()
                process.wait()
                _ended_before_ready(
                    app,
                    session_id,
                    read_to_end(read_end),
                    f"The session wasn't ready after {limit:g} seconds and was ended.",
                    DATA_ERROR,
                )
            time.sleep(0.05)
            entry = read_entry(session_id)
    finally:
        # Once the session is ready, it reads the pipe itself.
        os.close(read_end)

    answer = _expect(OutputAnswer, entry, SessionRequest(Request.WAIT), max(0.0, deadline - time.monotonic()))
    if _structured(app):
        app.print_data({"id": session_id, **as_dict(answer, remove_defaults=True)})
    else:
        app.echo(f"Started session {session_id}.")
        _echo_answer(app, entry, answer)
    app.exit(_exit_code(answer))


def _ended_before_ready(app: Application, session_id: str, output: str, message: str, exit_code: int) -> None:
    remove_session_files(session_id)
    if output:
        app.echo(output, nl=False)
    app.error(message)
    app.exit(exit_code)


@session.command()
@_timeout_option("the answer")
@click.argument("session_id", metavar="ID")
@click.argument("text", metavar="INPUT")
@pass_application
def send(app: Application, timeout: float, session_id: str, text: str) -> None:
    """\
    Give INPUT to the prompt of the session ID and print its output up to the next prompt.

    INPUT is a whole input: a statement, a text of several lines such as a FOR
    loop with its END, or a dot-command such as `.vars`, which works as at the
    prompt, each in a send of its own. A block that INPUT leaves unfinished
    fails. The exit code is 0 when the statement passed, 1 when it failed, and
    124 when it still runs after `--timeout`. When the REPL or the run ends,
    `send` says so with its exit code; a `send` after that fails, and
    `session restart` starts it again.
    """
    entry = _entry(session_id)
    answer = _expect(OutputAnswer, entry, SessionRequest(Request.SEND, text), timeout)
    _echo_answer(app, entry, answer)
    app.exit(_exit_code(answer))


@session.command()
@_timeout_option("the next prompt")
@click.argument("session_id", metavar="ID")
@pass_application
def wait(app: Application, timeout: float, session_id: str) -> None:
    """\
    Wait until the session ID waits at its prompt or its REPL or run has ended, and print its output since the last
    command.

    Takes over from a `send` that returned after its `--timeout`, with the exit
    code that `send` would have had.
    """
    entry = _entry(session_id)
    answer = _expect(OutputAnswer, entry, SessionRequest(Request.WAIT), timeout)
    _echo_answer(app, entry, answer)
    app.exit(_exit_code(answer))


@session.command(name="status")
@click.argument("session_id", metavar="ID")
@pass_application
def session_status(app: Application, session_id: str) -> None:
    """\
    Print whether the session ID runs, waits at its prompt or its REPL or run has ended: `runs`, `waits` or `ended`.

    It takes none of the output of the session, which `session wait` prints.
    """
    answer = _expect(StateAnswer, _entry(session_id), SessionRequest(Request.STATE))
    if _structured(app):
        app.print_data(answer)
    else:
        app.echo(str(answer.state))


@session.command(name="result")
@click.argument("session_id", metavar="ID")
@pass_application
def session_result(app: Application, session_id: str) -> None:
    """\
    Print the exit code of the REPL or the run of the session ID once it has ended.

    `result` itself exits with 0, as Robot Framework gives exit codes a meaning
    of its own; before the end, it says so and exits with 252.
    """
    answer = _expect(ResultAnswer, _entry(session_id), SessionRequest(Request.RESULT))
    if _structured(app):
        app.print_data(answer)
    else:
        app.echo(str(answer.exit_code))


@session.command()
@_timeout_option("the first prompt")
@click.argument("session_id", metavar="ID")
@pass_application
def restart(app: Application, timeout: float, session_id: str) -> None:
    """\
    Start the REPL or the run of the session ID again in a new process, and print its output up to its first prompt
    or its end.

    A REPL or a run that hasn't ended is ended as with `session stop`, and its
    output since the last command comes first. The session keeps its ID, and
    the new process starts with the options of `session start` and the
    breakpoints as they are.
    """
    entry = _entry(session_id)
    # The old process ends the REPL or the run as `stop` does, then waits for the new process to take commands.
    restarted = _request(entry, SessionRequest(Request.RESTART), 2 * _STARTUP_LIMIT)
    if not isinstance(restarted, RestartedAnswer):
        # After its limit, `restart` gets the output so far, while the restart goes on.
        if isinstance(restarted, (OutputAnswer, RestartFailedAnswer)) and restarted.output:
            app.echo(restarted.output, nl=False)
        if isinstance(restarted, RestartFailedAnswer):
            raise click.ClickException(restarted.reason)
        raise click.ClickException(f"Session '{session_id}' hasn't restarted yet; `session status` tells when it has.")
    before = restarted.output
    # The file names the new process now.
    entry = _entry(session_id)
    answer = _expect(OutputAnswer, entry, SessionRequest(Request.WAIT), timeout)
    if _structured(app):
        whole = dataclasses.replace(answer, output=before + answer.output)
        app.print_data({"id": session_id, **as_dict(whole, remove_defaults=True)})
    else:
        if before:
            app.echo(before, nl=not before.endswith("\n"))
        app.echo(f"Restarted session {session_id}.")
        _echo_answer(app, entry, answer)
    app.exit(_exit_code(answer))


@session.command()
@click.argument("session_id", metavar="ID")
def interrupt(session_id: str) -> None:
    """\
    Interrupt the session ID as Ctrl-C does at its terminal.

    In a REPL, the statement that runs fails; with the debugger attached, the run
    pauses at the next keyword. `session wait` prints what follows.
    """
    _request(_entry(session_id), SessionRequest(Request.INTERRUPT))


@session.command()
@click.option("--project", "of_project", is_flag=True, help="End the sessions of the project of the current folder.")
@click.option("--all", "all_sessions", is_flag=True, help="End all your sessions.")
@click.argument("session_id", metavar="[ID]", required=False)
@pass_application
def stop(app: Application, of_project: bool, all_sessions: bool, session_id: Optional[str]) -> None:
    """\
    End the session ID and print its output since the last command, or end several sessions.

    `--project` ends the sessions of the project the current folder belongs to,
    the folder RobotCode finds for its `robot.toml`; a session belongs to the
    project of the folder `session start` ran in. `--all` ends all your
    sessions. A debug run that has not ended is aborted as with `.abort`.
    """
    if (session_id is not None) + of_project + all_sessions != 1:
        raise click.UsageError("Give the ID of a session, --project or --all.")
    if session_id is not None:
        answer = _stop(_entry(session_id))
        if answer.output:
            app.echo(answer.output, nl=False)
        return

    entries = open_sessions()
    if of_project:
        project = project_folder(app)
        entries = [entry for entry in entries if same_file(entry.project, project)]
    if not entries:
        app.echo("No session is open.")
    for entry in entries:
        # It can have ended since it was listed.
        if read_entry(entry.id) is not None:
            _stop(entry)
            app.echo(f"Stopped session {entry.id}.")


def _stop(entry: SessionEntry) -> StoppedAnswer:
    answer = _request(entry, SessionRequest(Request.STOP), 60)
    if not isinstance(answer, StoppedAnswer):
        raise click.ClickException(f"Session '{entry.id}' hasn't ended yet; a second `session stop` ends it at once.")
    return answer


@session.command(name="list")
@pass_application
def list_sessions(app: Application) -> None:
    """List the open sessions with their project folder, whether they run, wait or their REPL or run has ended, and
    the time left until they end for being idle."""
    entries = open_sessions()
    if _structured(app):
        app.print_data(
            [
                {
                    "id": entry.id,
                    "project": entry.project,
                    "state": entry.state,
                    "time_left": None if (left := entry.time_left()) is None else round(left),
                }
                for entry in entries
            ]
        )
        return
    if not entries:
        app.echo("No session is open.")
        return
    rows = [("ID", "PROJECT", "STATE", "IDLE TIME LEFT")] + [
        (entry.id, entry.project, entry.state, _minutes(entry.time_left())) for entry in entries
    ]
    widths = [max(len(row[column]) for row in rows) for column in range(3)]
    for row in rows:
        app.echo("  ".join([*(cell.ljust(width) for cell, width in zip(row, widths)), row[3]]))


def _minutes(seconds: Optional[float]) -> str:
    if seconds is None:
        return "-"
    minutes, seconds = divmod(round(seconds), 60)
    return f"{minutes}:{seconds:02d}"


def _entry(session_id: str) -> SessionEntry:
    entry = read_entry(session_id)
    if entry is None:
        raise click.ClickException(f"No session '{session_id}' is open.")
    return entry


def _request(entry: SessionEntry, request: SessionRequest, timeout: Optional[float] = None) -> SessionAnswer:
    """The answer of the session `entry` to `request`; after `timeout` seconds, the output so far."""
    answer = _ask(entry, request, timeout)
    while isinstance(answer, MovedAnswer):
        # The session has just restarted in a new process, which its file names now.
        moved_to = read_entry(entry.id)
        if moved_to is None or moved_to.address == entry.address:
            raise click.ClickException(f"No session '{entry.id}' is open.")
        entry = moved_to
        answer = _ask(entry, request, timeout)
    if isinstance(answer, RefusedAnswer):
        raise click.ClickException(answer.message)
    return answer


def _expect(answer_type: Type[A], entry: SessionEntry, request: SessionRequest, timeout: Optional[float] = None) -> A:
    """The answer of the session `entry` to a `request` that only an `answer_type` answers."""
    answer = _request(entry, request, timeout)
    if not isinstance(answer, answer_type):
        raise click.ClickException(f"Session '{entry.id}' gave an unexpected answer.")
    return answer


def _ask(entry: SessionEntry, request: SessionRequest, timeout: Optional[float]) -> ChannelAnswer:
    """Send `request` to the process that `entry` names and return its answer; after `timeout` seconds, the output so
    far."""
    try:
        with connect(entry) as connection:
            connection.send(request)
            if timeout is not None and not connection.poll(timeout):
                try:
                    connection.send(SessionRequest(Request.STATUS))
                except OSError:
                    # The answer came just now, and the session has closed the connection.
                    pass
            answer: ChannelAnswer = connection.recv()
    except (OSError, EOFError, multiprocessing.AuthenticationError) as e:
        raise click.ClickException(f"Session '{entry.id}' doesn't answer: {e or type(e).__name__}") from e
    return answer


def _structured(app: Application) -> bool:
    return app.config.output_format not in (None, OutputFormat.TEXT)


def _echo_answer(app: Application, entry: SessionEntry, answer: OutputAnswer) -> None:
    if _structured(app):
        app.print_data(answer)
        return
    if answer.output:
        app.echo(answer.output, nl=False)
        if not answer.output.endswith("\n"):
            app.echo("")
    if answer.exit_code is not None:
        app.echo(f"{entry.kind.what} has ended with exit code {answer.exit_code}.", err=True)
    elif answer.status is AnswerStatus.RUNNING:
        app.echo(f"It still runs; `robotcode session wait {entry.id}` prints the rest.", err=True)


def _exit_code(answer: OutputAnswer) -> int:
    """How the input went; the exit code of the REPL or the run is in the output."""
    return _EXIT_CODES[answer.status]
