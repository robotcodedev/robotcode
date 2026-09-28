"""Tests for recording the unhandled failures of a REPL session.

While `record_failures` is set (by `robotcode repl`), `BaseInterpreter.run`
records what fails without being handled; the `repl` marker keyword then fails
the session test with it (see `test_run.py`). These tests feed the prompt loop
the exceptions directly, without running Robot.
"""

from datetime import datetime
from typing import Any, Iterator, List, Optional, Union

import pytest
from robot.errors import ExecutionFailed, ExecutionFailures, PassExecution
from robot.running import Keyword

from robotcode.plugin import Application
from robotcode.repl._debug.controller import DebugController
from robotcode.repl.base_interpreter import BaseInterpreter, ExecutionInterrupted
from robotcode.repl.console_interpreter import ConsoleInterpreter


class _Loop(BaseInterpreter):
    """Raises each of `outcomes` from one input — `None` is an input that runs
    cleanly — then ends the session like Ctrl-D."""

    def __init__(self, outcomes: List[Optional[BaseException]], *, record_failures: bool = True) -> None:
        super().__init__()
        self.record_failures = record_failures
        self._outcomes = list(outcomes)
        self.logged: List[str] = []

    def get_input(self) -> Iterator[Optional[Keyword]]:
        if not self._outcomes:
            raise EOFError
        outcome = self._outcomes.pop(0)
        if outcome is not None:
            raise outcome
        return iter(())

    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        self.logged.append(f"{level}: {message}")

    def message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        pass


def _run(*outcomes: Optional[BaseException], record_failures: bool = True) -> _Loop:
    loop = _Loop(list(outcomes), record_failures=record_failures)
    loop.run()
    return loop


def _messages(failures: List[ExecutionFailed]) -> List[str]:
    return [str(failure) for failure in failures]


def test_failure_stays_recorded_after_later_input() -> None:
    failure = ExecutionFailed("boom")

    loop = _run(failure, None)

    assert loop.failures == [failure]


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(ExecutionFailed("fatal", exit=True), id="fatal-error"),
        pytest.param(ExecutionFailed("continued", continue_on_failure=True), id="continue-on-failure"),
    ],
)
def test_failure_variants_are_recorded(failure: ExecutionFailed) -> None:
    assert _run(failure).failures == [failure]


def test_several_failures_of_one_input_are_recorded_one_by_one() -> None:
    one, two = ExecutionFailed("one"), ExecutionFailed("two")

    assert _run(ExecutionFailures([one, two])).failures == [one, two]


def test_skip_is_not_recorded() -> None:
    assert _run(ExecutionFailed("skipped", skip=True)).failures == []


def test_skip_after_a_continued_failure_is_not_recorded() -> None:
    # Robot Framework marks such a test SKIP; the continued failure is only part of its message.
    skip = ExecutionFailures([ExecutionFailed("early", continue_on_failure=True), ExecutionFailed("later", skip=True)])

    assert _run(skip).failures == []


def test_pass_execution_is_not_recorded() -> None:
    assert _run(PassExecution("passed")).failures == []


def test_failure_continued_before_pass_execution_is_recorded() -> None:
    early = ExecutionFailed("early", continue_on_failure=True)
    passed = PassExecution("done")
    passed.set_earlier_failures([early])

    assert _run(passed).failures == [early]


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(ExecutionInterrupted("Execution interrupted"), id="interrupted"),
        pytest.param(SyntaxError("Non-existing setting 'Foo'."), id="token-error"),
    ],
)
def test_logged_errors_are_recorded_as_failures(error: BaseException) -> None:
    loop = _run(error)

    assert _messages(loop.failures) == [str(error)]
    assert loop.logged == [f"ERROR: {error}"]


def _raise_runtime_error(kw: Keyword, context: Any) -> Any:
    raise RuntimeError("broken")


def test_error_swallowed_by_run_keyword_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("robotcode.repl.base_interpreter._run_keyword", _raise_runtime_error)
    loop = _Loop([])

    assert loop.run_keyword(Keyword("Log")) is None

    assert _messages(loop.failures) == ["<class 'RuntimeError'>: broken"]
    assert loop.logged == ["ERROR: <class 'RuntimeError'>: broken"]


def test_end_of_input_records_nothing() -> None:
    assert _run().failures == []


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(ExecutionFailed("boom"), id="failure"),
        pytest.param(ExecutionInterrupted("Execution interrupted"), id="interrupted"),
        pytest.param(SyntaxError("Non-existing setting 'Foo'."), id="token-error"),
    ],
)
def test_nothing_is_recorded_without_the_flag(error: BaseException) -> None:
    passed = PassExecution("done")
    passed.set_earlier_failures([ExecutionFailed("early")])

    loop = _run(error, passed, record_failures=False)

    assert loop.failures == []


def test_error_swallowed_by_run_keyword_is_not_recorded_without_the_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("robotcode.repl.base_interpreter._run_keyword", _raise_runtime_error)
    loop = _Loop([], record_failures=False)

    loop.run_keyword(Keyword("Log"))

    assert loop.failures == []


def _reader(lines: List[str]) -> Any:
    """A scripted `read_line` — pops queued lines, then signals EOF."""

    def read_line(prompt: str, **kwargs: Any) -> str:
        if not lines:
            raise EOFError
        return lines.pop(0)

    return read_line


def test_dot_command_usage_messages_are_not_recorded(capsys: pytest.CaptureFixture[str]) -> None:
    interpreter = ConsoleInterpreter(app=Application())
    interpreter.record_failures = True
    interpreter.read_line = _reader([".save", ".exit abc"])  # type: ignore[method-assign]

    interpreter.run()

    output = capsys.readouterr().out
    assert "Usage: .save" in output
    assert "Usage: .exit" in output
    assert interpreter.failures == []


def test_keyword_evaluated_at_a_debugger_stop_is_not_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("robotcode.repl.base_interpreter._run_keyword", _raise_runtime_error)
    interpreter = ConsoleInterpreter(app=None)
    interpreter.set_controller(DebugController())
    interpreter.record_failures = True

    interpreter._evaluate_at_stop("Log    hi")

    assert interpreter.failures == []
    # Recording goes on at the prompt once the stop is over.
    assert interpreter.record_failures is True
