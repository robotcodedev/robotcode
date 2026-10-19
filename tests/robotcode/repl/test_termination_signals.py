"""How the patched stop-signal monitor handles SIGINT and SIGTERM.

Most tests call the monitor directly, the way the operating system would call it
as a signal handler. The prompt_toolkit tests send a real SIGTERM, because the
prompt has to end from wherever its event loop is when the signal arrives.
"""

import contextlib
import io
import signal
import sys
import threading
from typing import Any, Callable, Iterator, Tuple

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput
from robot.errors import ExecutionFailed
from robot.running.signalhandler import _StopSignalMonitor

from robotcode.plugin import Application
from robotcode.repl import base_interpreter
from robotcode.repl._debug.controller import DebugController
from robotcode.repl._debug.types import StackFrame, StopEvent, StopReason
from robotcode.repl.base_interpreter import ExecutionInterrupted
from robotcode.repl.console_interpreter import ConsoleInterpreter
from robotcode.repl.prompt_toolkit_interpreter import PromptToolkitConsoleInterpreter
from robotcode.repl_server.interpreter import Interpreter as ReplServerInterpreter


class _ExitError(Exception):
    """Raised by the fake `os._exit`."""


@pytest.fixture(autouse=True)
def _signal_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(base_interpreter, "_ending_signal_count", 0)
    monkeypatch.setattr(base_interpreter, "_signal_ends_run", False)
    monkeypatch.setattr(base_interpreter, "_signal_interpreter", None)

    def fake_exit(code: int) -> None:
        raise _ExitError(code)

    monkeypatch.setattr("robotcode.repl.base_interpreter.os._exit", fake_exit)


def _session(in_repl_run: bool = True) -> ConsoleInterpreter:
    interpreter = ConsoleInterpreter(app=None)
    interpreter._in_repl_run = in_repl_run
    return interpreter


def _monitor(running_keyword: bool) -> _StopSignalMonitor:
    monitor = _StopSignalMonitor()
    monitor._running_keyword = running_keyword
    return monitor


def test_sigint_interrupts_the_running_keyword() -> None:
    interpreter = _session()

    with pytest.raises(ExecutionInterrupted, match="Execution interrupted"):
        _monitor(running_keyword=True)(signal.SIGINT, None)
    assert not interpreter._termination_requested


def test_sigint_without_a_running_keyword_changes_nothing() -> None:
    interpreter = _session()

    _monitor(running_keyword=False)(signal.SIGINT, None)

    assert not interpreter._termination_requested
    assert interpreter.exit_code is None


def _debugged(
    *, in_repl_run: bool = False, running_statement: bool = False
) -> Tuple[ConsoleInterpreter, DebugController]:
    """An interpreter whose attached debugger sees the keywords that run: those of a robot-debug run by default."""
    interpreter = ConsoleInterpreter(app=Application())
    interpreter._in_repl_run = in_repl_run
    interpreter._running_statement = running_statement
    interpreter._logger.enabled = True
    controller = DebugController()
    interpreter.set_controller(controller)
    return interpreter, controller


@pytest.mark.parametrize(
    ("in_repl_run", "running_statement"),
    [pytest.param(False, False, id="robot-debug-run"), pytest.param(True, True, id="repl-statement")],
)
def test_sigint_with_the_debugger_attached_pauses_at_the_next_keyword(
    in_repl_run: bool, running_statement: bool, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _interpreter, controller = _debugged(in_repl_run=in_repl_run, running_statement=running_statement)
    # Robot Framework captures what a running keyword prints; the message must get past it.
    monkeypatch.setattr(sys, "stdout", io.StringIO())

    # Returns instead of raising: the keyword that runs goes on.
    _monitor(running_keyword=True)(signal.SIGINT, None)

    assert controller.pause_requested
    assert "Pausing at the next keyword (Ctrl-C again interrupts the keyword that runs)." in capfd.readouterr().out


def test_sigint_pauses_even_when_its_message_cannot_be_written(monkeypatch: pytest.MonkeyPatch) -> None:
    interpreter, controller = _debugged()

    def refuse(*args: Any, **kwargs: Any) -> None:
        # What a write raises when the signal interrupted another write to the same stream.
        raise RuntimeError("reentrant call inside <_io.BufferedWriter name='<stdout>'>")

    monkeypatch.setattr(interpreter.app, "echo", refuse)

    _monitor(running_keyword=True)(signal.SIGINT, None)

    assert controller.pause_requested


def test_second_sigint_interrupts_the_running_keyword() -> None:
    _interpreter, controller = _debugged()
    monitor = _monitor(running_keyword=True)
    monitor(signal.SIGINT, None)

    with pytest.raises(ExecutionInterrupted, match="Execution interrupted"):
        monitor(signal.SIGINT, None)
    assert controller.pause_requested


def _detached_in_a_repl_statement(interpreter: ConsoleInterpreter, controller: DebugController) -> None:
    interpreter._in_repl_run = True
    interpreter._running_statement = True
    controller.set_attached(False)


def _at_a_stop(interpreter: ConsoleInterpreter, controller: DebugController) -> None:
    frame = StackFrame(name="Sleep", type="KEYWORD", source=None, line=None, depth=0)
    interpreter._stop = StopEvent(reason=StopReason.ENTRY, frame=frame, stack=[frame])


def _between_statements(interpreter: ConsoleInterpreter, controller: DebugController) -> None:
    interpreter._in_repl_run = True


def _before_the_session(interpreter: ConsoleInterpreter, controller: DebugController) -> None:
    interpreter._logger.enabled = False


@pytest.mark.parametrize(
    "situation",
    [
        pytest.param(_detached_in_a_repl_statement, id="repl-statement-detached"),
        pytest.param(_at_a_stop, id="at-a-stop"),
        pytest.param(_between_statements, id="repl-between-statements"),
        pytest.param(_before_the_session, id="events-not-forwarded"),
    ],
)
def test_sigint_interrupts_the_running_keyword_where_nothing_pauses(
    situation: Callable[[ConsoleInterpreter, DebugController], None],
) -> None:
    interpreter, controller = _debugged()
    situation(interpreter, controller)

    with pytest.raises(ExecutionInterrupted, match="Execution interrupted"):
        _monitor(running_keyword=True)(signal.SIGINT, None)
    assert not controller.pause_requested


def test_sigint_without_the_debugger_ends_a_robot_debug_run() -> None:
    _interpreter, controller = _debugged()
    controller.set_attached(False)

    with pytest.raises(ExecutionFailed, match="Execution terminated by signal") as error:
        _monitor(running_keyword=True)(signal.SIGINT, None)
    # Robot Framework's own failure, which ends the run.
    assert error.value.exit


def test_sigint_without_the_debugger_ends_the_run_at_the_next_keyword() -> None:
    _interpreter, controller = _debugged()
    controller.set_attached(False)
    monitor = _monitor(running_keyword=False)

    monitor(signal.SIGINT, None)

    with pytest.raises(ExecutionFailed, match="Execution terminated by signal"):
        monitor.start_running_keyword(in_teardown=False)


@pytest.mark.parametrize("first", [signal.SIGINT, signal.SIGTERM], ids=["after-sigint", "after-sigterm"])
def test_second_signal_ends_a_run_without_the_debugger_at_once(first: signal.Signals) -> None:
    _interpreter, controller = _debugged()
    controller.set_attached(False)
    monitor = _monitor(running_keyword=False)
    monitor(first, None)

    with pytest.raises(_ExitError) as exited:
        monitor(signal.SIGINT, None)
    assert exited.value.args == (253,)


def test_sigint_in_repl_server_interrupts_the_running_keyword() -> None:
    # The notebook kernel interrupts a cell this way; `repl-server` has no debugger to pause.
    interpreter = ReplServerInterpreter()
    interpreter._logger.enabled = True

    with pytest.raises(ExecutionInterrupted, match="Execution interrupted"):
        _monitor(running_keyword=True)(signal.SIGINT, None)


def test_sigterm_interrupts_the_keyword_and_ends_the_session() -> None:
    interpreter = _session()

    with pytest.raises(ExecutionInterrupted, match="Execution terminated by signal"):
        _monitor(running_keyword=True)(signal.SIGTERM, None)
    assert interpreter._termination_requested
    assert interpreter.exit_code == 253


def test_sigterm_ends_an_idle_session() -> None:
    interpreter = _session()
    monitor = _monitor(running_keyword=False)

    monitor(signal.SIGTERM, None)

    assert interpreter._termination_requested
    assert interpreter.exit_code == 253
    # Nothing runs, so nothing is stopped: the session test isn't failed by the signal.
    monitor.start_running_keyword(in_teardown=False)


def test_sigterm_between_two_keywords_stops_the_statement_at_the_next_keyword() -> None:
    interpreter = _session()
    interpreter._running_statement = True
    monitor = _monitor(running_keyword=False)

    monitor(signal.SIGTERM, None)

    assert interpreter._termination_requested
    with pytest.raises(ExecutionInterrupted, match="Execution terminated by signal"):
        monitor.start_running_keyword(in_teardown=False)


def test_sigterm_outside_a_session_stops_the_run_like_robot_framework() -> None:
    interpreter = _session(in_repl_run=False)

    with pytest.raises(ExecutionFailed, match="Execution terminated by signal") as error:
        _monitor(running_keyword=True)(signal.SIGTERM, None)
    assert error.value.exit
    assert interpreter._termination_requested
    assert interpreter.exit_code is None


@pytest.mark.parametrize("in_repl_run", [True, False], ids=["session", "run"])
@pytest.mark.parametrize("running_keyword", [False, True], ids=["idle", "keyword-runs"])
def test_sigterm_detaches_the_debugger(in_repl_run: bool, running_keyword: bool) -> None:
    interpreter = _session(in_repl_run=in_repl_run)
    controller = DebugController()
    interpreter.set_controller(controller)

    with contextlib.suppress(ExecutionFailed, ExecutionInterrupted):
        _monitor(running_keyword=running_keyword)(signal.SIGTERM, None)

    assert not controller.attached


def test_second_sigterm_forces_the_end() -> None:
    _session()
    monitor = _monitor(running_keyword=False)
    monitor(signal.SIGTERM, None)

    with pytest.raises(_ExitError) as exited:
        monitor(signal.SIGTERM, None)
    assert exited.value.args == (253,)


def test_sigterm_ends_a_read_once_it_has_arrived() -> None:
    interpreter = _session()
    _monitor(running_keyword=False)(signal.SIGTERM, None)

    with pytest.raises(EOFError):
        interpreter._read(">>> ")


# ---------------------------------------------------------------------------
# prompt_toolkit prompt, with a real SIGTERM
# ---------------------------------------------------------------------------

needs_sigterm = pytest.mark.skipif(sys.platform == "win32", reason="Windows doesn't deliver SIGTERM to a handler")


@pytest.fixture
def pipe_input() -> Iterator[PipeInput]:
    with create_pipe_input() as inp:
        with create_app_session(input=inp, output=DummyOutput()):
            yield inp


@pytest.fixture
def sigterm_monitor() -> Iterator[None]:
    previous = signal.signal(signal.SIGTERM, _StopSignalMonitor())
    yield
    signal.signal(signal.SIGTERM, previous)


def _prompt_toolkit_session() -> PromptToolkitConsoleInterpreter:
    interpreter = PromptToolkitConsoleInterpreter(app=None, no_history=True)
    interpreter._in_repl_run = True
    return interpreter


def _once_drawn(interpreter: PromptToolkitConsoleInterpreter, action: Any) -> None:
    """Run `action` after the prompt is first drawn; its event loop then waits for input."""
    app = interpreter._session.app

    def after_render(_: Any) -> None:
        app.after_render -= after_render
        action(app)

    app.after_render += after_render


def _read(interpreter: PromptToolkitConsoleInterpreter, pipe_input: PipeInput) -> str:
    # Enter keys end the prompt if SIGTERM doesn't, so a failure can't hang the run.
    done = threading.Event()

    def press_enter() -> None:
        while not done.wait(5):
            pipe_input.send_text("\r")

    threading.Thread(target=press_enter, daemon=True).start()
    try:
        return interpreter._read(">>> ")
    finally:
        done.set()


@needs_sigterm
def test_sigterm_ends_the_prompt_toolkit_prompt_waiting_for_input(pipe_input: PipeInput, sigterm_monitor: None) -> None:
    interpreter = _prompt_toolkit_session()
    main_thread = threading.main_thread().ident
    assert main_thread is not None
    _once_drawn(
        interpreter,
        # the test is skipped on Windows, which has no `signal.pthread_kill`
        lambda app: threading.Thread(
            target=signal.pthread_kill,  # type: ignore[attr-defined,unused-ignore]
            args=(main_thread, signal.SIGTERM),
        ).start(),
    )

    with pytest.raises(EOFError):
        _read(interpreter, pipe_input)
    assert interpreter.exit_code == 253


@needs_sigterm
def test_sigterm_in_a_callback_of_the_prompt_loop_ends_the_prompt_toolkit_prompt(
    pipe_input: PipeInput, sigterm_monitor: None
) -> None:
    # The handler runs inside the callback, where an error raised by it would only be reported.
    interpreter = _prompt_toolkit_session()
    _once_drawn(interpreter, lambda app: app.loop.call_soon(signal.raise_signal, signal.SIGTERM))

    with pytest.raises(EOFError):
        _read(interpreter, pipe_input)
    assert interpreter.exit_code == 253
