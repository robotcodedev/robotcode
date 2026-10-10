"""Tests for REPL input that does not parse.

Invalid statements run like in a `robot` test body: Robot Framework fails them
when execution reaches them. Only an unfinished block waits for more lines,
input that ends inside one is still reported, and a line starting with `...`
never runs as a statement of its own.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import IO, Any, AnyStr, Callable, Iterator, List, Optional, Sequence, Tuple, Union

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput
from robot.api import ExecutionResult
from robot.errors import ExecutionFailed
from robot.result import Message

from robotcode.plugin import Application
from robotcode.repl.console_interpreter import ConsoleInterpreter
from robotcode.repl.prompt_toolkit_interpreter import PromptToolkitConsoleInterpreter
from robotcode.repl.run import run_repl
from robotcode.robot.utils import RF_VERSION

_RETURN_MESSAGE = (
    "RETURN is not allowed in this context."
    if RF_VERSION >= (6, 1)
    else "RETURN can only be used inside a user keyword."
)

_ORPHAN_MESSAGE = "The line starting with '...' does not continue a statement, it starts a new input."


class _Reader:
    """Scripted `read_line` — pops queued lines, then signals EOF. Records whether
    it was asked again after EOF, which blocks on a real terminal."""

    def __init__(self, lines: Sequence[str]) -> None:
        self._lines = list(lines)
        self.ended = False
        self.read_after_end = False

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        if self._lines:
            return self._lines.pop(0)
        if self.ended:
            self.read_after_end = True
        self.ended = True
        raise EOFError


class _Stdin:
    """Stands in for `sys.stdin`, which decides whether `get_input` shows prompts."""

    def __init__(self, *, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


class _EchoApp(Application):
    """Real `Application` whose echo channel captures into a list."""

    def __init__(self) -> None:
        super().__init__()
        self.echoed: List[str] = []

    def echo(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: bool = True,
        err: bool = False,
    ) -> None:
        self.echoed.append(message() if callable(message) else str(message))


class _Session(ConsoleInterpreter):
    """A plain REPL session fed from script files and scripted prompt lines that
    collects what Robot Framework logs instead of printing it."""

    def __init__(self, *, files: Sequence[Path] = (), lines: Sequence[str] = (), inspect: bool = False) -> None:
        super().__init__(app=None, files=list(files), inspect=inspect)
        self.reader = _Reader(lines)
        self.read_line = self.reader  # type: ignore[method-assign]
        self.logged: List[Tuple[str, str]] = []

    def log_message(
        self, message: str, level: str, html: Union[str, bool] = False, timestamp: Union[datetime, str, None] = None
    ) -> None:
        self.logged.append((level, message))

    def messages(self, level: str) -> List[str]:
        return [message for logged_level, message in self.logged if logged_level == level]


def _run(project: Path, session: _Session, **options: Any) -> None:
    app = Application()
    app.config.root = project
    run_repl(interpreter=session, app=app, outputdir=str(project / "results"), **options)


def _script(project: Path, name: str, text: str) -> Path:
    path = project / name
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# `parse_input` — the non-raising entry point for REPL input
# ---------------------------------------------------------------------------


def _parse(text: str) -> Any:
    return ConsoleInterpreter(app=None).parse_input(text)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("FOR    ${i}    IN    1    2\n    Log    ${i}", id="open-for"),
        pytest.param("FOR    ${i}    IN    1\n    IF    True\n        Log    x\n    END", id="nested-open"),
        pytest.param("IF    True", id="header-only-if"),
        pytest.param("WHILE    True", id="header-only-while"),
        pytest.param("TRY", id="header-only-try"),
    ],
)
def test_block_without_end_is_incomplete(text: str) -> None:
    parsed = _parse(text)

    assert parsed.incomplete
    assert parsed.errors


@pytest.mark.parametrize(
    ("text", "has_errors"),
    [
        pytest.param("FOR    ${i}    IN    1\n    Log    ${i}\nEND", False, id="closed-for"),
        pytest.param("IF    True    Log    a    ELSE    Log    b", False, id="inline-if"),
        pytest.param("IF    True    Log    a    ELSE", True, id="inline-if-with-empty-else"),
        pytest.param("IF    True\n    Log    a\nELSE\nEND", True, id="empty-else"),
        pytest.param("RETURN    x", True, id="top-level-return"),
        pytest.param("IF    True\n    RETURN    x\nEND", True, id="nested-return"),
        # Before RF 6.1 a stray END is a keyword call that fails when it runs.
        pytest.param("END", RF_VERSION >= (6, 1), id="stray-end"),
        # Lowercase `for` is a keyword call, not a block.
        pytest.param("for    ${i}    IN    1", False, id="lowercase-for"),
    ],
)
def test_complete_input_is_not_incomplete(text: str, has_errors: bool) -> None:
    parsed = _parse(text)

    assert not parsed.incomplete
    assert bool(parsed.errors) == has_errors


def test_group_without_end_is_incomplete_where_group_is_a_block() -> None:
    # GROUP is a block since Robot Framework 7.2 and a keyword call before.
    assert _parse("GROUP    g\n    Log    x").incomplete == (RF_VERSION >= (7, 2))


def test_token_error_is_returned_instead_of_raised() -> None:
    parsed = _parse("[Foo]    bar")

    assert parsed.errors == ["Non-existing setting 'Foo'."]
    assert not parsed.incomplete


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("[Foo]    bar", id="setting"),
        pytest.param(
            "END",
            id="stray-end",
            marks=pytest.mark.skipif(RF_VERSION < (6, 1), reason="a token error since Robot Framework 6.1"),
        ),
    ],
)
def test_old_entry_point_still_raises_on_token_errors(text: str) -> None:
    # `robotcode repl-server` relies on this `SyntaxError`.
    with pytest.raises(SyntaxError):
        ConsoleInterpreter(app=None).get_test_body_from_string(text)


# ---------------------------------------------------------------------------
# Script files run like a test body
# ---------------------------------------------------------------------------

_INVALID_STATEMENTS: List[Any] = [
    pytest.param("FOR    ${i}    IN    1    2\n    Log    ${i}", "FOR loop must have closing END.", id="unclosed-for"),
    pytest.param("IF    True\n    Log    a\nELSE\nEND", "ELSE branch cannot be empty.", id="empty-else"),
    # Robot Framework 5.0 fails an invalid TRY without logging why; the REPL logs it.
    pytest.param("TRY\n    Log    a\nEND", "TRY structure must have EXCEPT or FINALLY branch.", id="invalid-try"),
    pytest.param("RETURN    x", _RETURN_MESSAGE, id="top-level-return"),
]


@pytest.mark.parametrize(("statement", "message"), _INVALID_STATEMENTS)
def test_script_runs_up_to_the_invalid_statement(statement: str, message: str, project: Path) -> None:
    broken = _script(project, "broken.robotrepl", f"Log    BEFORE\n{statement}\nLog    AFTER\n")
    later = _script(project, "later.robotrepl", "Log    LATER\n")
    session = _Session(files=[broken, later])

    _run(project, session)

    assert "BEFORE" in session.messages("INFO")
    assert session.messages("FAIL") == [message]
    assert "AFTER" not in session.messages("INFO")
    assert "a" not in session.messages("INFO")
    assert "LATER" in session.messages("INFO")


def test_prompt_opens_after_a_broken_script_with_inspect(project: Path) -> None:
    broken = _script(project, "broken.robotrepl", "FOR    ${i}    IN    1\n    Log    ${i}\n")
    session = _Session(files=[broken], lines=["Log    PROMPT"], inspect=True)

    _run(project, session)

    assert session.messages("FAIL") == ["FOR loop must have closing END."]
    assert "PROMPT" in session.messages("INFO")


def test_error_in_a_branch_that_is_not_executed_is_not_reported(project: Path) -> None:
    script = _script(project, "script.robotrepl", "IF    False\n    RETURN    x\nEND\nLog    AFTER\n")
    session = _Session(files=[script])

    _run(project, session)

    assert session.messages("FAIL") == []
    assert "AFTER" in session.messages("INFO")


def _steps(item: Any) -> Iterator[Any]:
    for step in getattr(item, "body", ()):
        yield step
        yield from _steps(step)


def test_failure_of_a_script_is_recorded_in_output_xml(project: Path) -> None:
    script = _script(project, "script.robotrepl", "FOR    ${i}    IN    1\n    Log    ${i}\n")

    _run(project, _Session(files=[script]), output="output.xml")

    [test] = ExecutionResult(str(project / "results" / "output.xml")).suite.tests
    [loop] = [step for step in _steps(test) if step.type == "FOR"]
    assert loop.status == "FAIL"
    # Older Robot Framework versions keep the message only as a FAIL message of the
    # step, as with `robot`.
    fail_messages = [item.message for item in loop.body if isinstance(item, Message) and item.level == "FAIL"]
    assert "FOR loop must have closing END." in [loop.message, *fail_messages]


def test_setting_error_without_a_statement_is_left_to_robot(project: Path, capfd: pytest.CaptureFixture[str]) -> None:
    script = _script(project, "script.robotrepl", "Log    BEFORE\n[Foo]    bar\nLog    AFTER\n")
    session = _Session(files=[script])
    session.record_failures = True

    _run(project, session)

    if RF_VERSION < (6, 1):
        # Robot Framework reports it while parsing and runs the rest, as `robot` does.
        assert "Non-existing setting 'Foo'." in capfd.readouterr().err
        assert session.messages("ERROR") == []
        assert session.messages("FAIL") == []
        assert session.failures == []
        assert {"BEFORE", "AFTER"} <= set(session.messages("INFO"))
    else:
        assert session.messages("FAIL") == ["Non-existing setting 'Foo'."]
        assert "AFTER" not in session.messages("INFO")


# ---------------------------------------------------------------------------
# Line-by-line input
# ---------------------------------------------------------------------------


def test_invalid_complete_block_runs_at_once(project: Path) -> None:
    session = _Session(lines=["IF    True", "    Log    a", "ELSE", "END", "Log    AFTER"])

    _run(project, session)

    assert session.messages("FAIL") == ["ELSE branch cannot be empty."]
    assert "AFTER" in session.messages("INFO")


def test_top_level_return_is_reported_without_an_extra_empty_line(project: Path) -> None:
    session = _Session(lines=["RETURN    x", "Log    AFTER"])

    _run(project, session)

    assert session.messages("FAIL") == [_RETURN_MESSAGE]
    assert "AFTER" in session.messages("INFO")


def test_continuation_line_inside_an_open_block_still_works(project: Path) -> None:
    session = _Session(lines=["FOR    ${i}    IN    1", "...    2", "    Log    ${i}", "END"])

    _run(project, session)

    assert session.messages("FAIL") == []
    assert session.messages("INFO") == ["1", "2"]


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="a stray EXCEPT is a token error since Robot Framework 6.1")
def test_token_error_inside_an_open_block_keeps_the_block_together(project: Path) -> None:
    session = _Session(lines=["FOR    ${i}    IN    1    2", "    EXCEPT", "    Log    ${i}", "END", "Log    AFTER"])

    _run(project, session)

    assert session.messages("FAIL") == ["EXCEPT is not allowed in this context."]
    assert session.messages("INFO") == ["AFTER"]


@pytest.mark.parametrize(
    "lines",
    [
        pytest.param(["FOR    ${i}    IN    1    2", "    Log    ${i}"], id="for"),
        pytest.param(["IF    True", "    Log    ${1}"], id="if"),
        pytest.param(["WHILE    True", "    Log    ${1}"], id="while"),
        pytest.param(["TRY", "    Log    ${1}"], id="try"),
    ],
)
def test_input_ending_inside_a_block_is_reported(lines: List[str], project: Path) -> None:
    session = _Session(lines=["Log    BEFORE", *lines])

    _run(project, session)

    [failure] = session.messages("FAIL")
    assert "must have closing END." in failure
    assert session.messages("INFO") == ["BEFORE"]
    assert not session.reader.read_after_end


def test_next_prompt_after_the_input_ended_does_not_read_again() -> None:
    interp = ConsoleInterpreter(app=None)
    reader = _Reader(["FOR    ${i}    IN    1"])
    interp.read_line = reader  # type: ignore[method-assign]

    assert [type(item).__name__ for item in interp.get_input()] == ["For"]
    with pytest.raises(EOFError):
        list(interp.get_input())
    assert not reader.read_after_end


@pytest.mark.parametrize(
    ("tty", "echoed"),
    [pytest.param(True, [""], id="terminal"), pytest.param(False, [], id="pipe")],
)
def test_input_ending_inside_a_block_ends_the_prompt_line(
    tty: bool, echoed: List[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # `input()` leaves the cursor after the prompt on EOF; piped input shows no prompt.
    monkeypatch.setattr(sys, "stdin", _Stdin(tty=tty))
    app = _EchoApp()
    interp = ConsoleInterpreter(app=app)
    interp.read_line = _Reader(["FOR    ${i}    IN    1"])  # type: ignore[method-assign]

    list(interp.get_input())

    assert app.echoed == echoed


def test_orphaned_continuation_line_fails_instead_of_running(project: Path) -> None:
    session = _Session(lines=["IF    True    Log    A    ELSE", "...    Log    B", "Log    AFTER"])
    session.record_failures = True

    _run(project, session)

    assert session.messages("FAIL") == ["ELSE branch cannot be empty.", _ORPHAN_MESSAGE]
    assert session.messages("INFO") == ["AFTER"]
    # It reaches the prompt loop like a failing statement.
    assert [str(failure) for failure in session.failures] == ["ELSE branch cannot be empty.", _ORPHAN_MESSAGE]


def test_orphaned_continuation_line_raises_a_failure() -> None:
    interp = ConsoleInterpreter(app=None)
    interp.read_line = _Reader(["...    Log    B"])  # type: ignore[method-assign]

    with pytest.raises(ExecutionFailed, match="does not continue a statement"):
        list(interp.get_input())


def test_save_exports_only_inputs_without_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    interp = ConsoleInterpreter(app=Application())
    interp.read_line = _Reader(  # type: ignore[method-assign]
        ["Log    one", "IF    True", "    Log    a", "ELSE", "END", "Log    two", ".save session.robot"]
    )

    for _ in range(4):  # three inputs, then `.save`
        list(interp.get_input())

    content = (tmp_path / "session.robot").read_text(encoding="utf-8")
    assert "Log    one" in content
    assert "Log    two" in content
    assert "ELSE" not in content


def _run_and_save(project: Path, lines: Sequence[str]) -> List[str]:
    """Runs `lines` at the prompt (the last one a `.save`) and returns what was echoed."""
    session = _Session(lines=lines)
    app = _EchoApp()
    session.app = app
    _run(project, session)
    return app.echoed


def test_save_leaves_out_inputs_whose_run_failed(project: Path) -> None:
    echoed = _run_and_save(
        project,
        ["Log    one", "No Such Keyword Here", "Should Be Equal    1    2", "Log    two", ".save session.robot"],
    )

    content = (project / "session.robot").read_text(encoding="utf-8")
    assert "Log    one" in content
    assert "Log    two" in content
    assert "No Such Keyword Here" not in content
    assert "Should Be Equal" not in content
    assert "Wrote session.robot (2 entries; 2 failed inputs left out, see --keep-failed)" in echoed


def test_save_keep_failed_exports_failed_inputs(project: Path) -> None:
    echoed = _run_and_save(project, ["Log    one", "No Such Keyword Here", ".save --keep-failed session.robot"])

    content = (project / "session.robot").read_text(encoding="utf-8")
    assert "Log    one" in content
    assert "No Such Keyword Here" in content
    assert "Wrote session.robot (2 entries)" in echoed


def test_save_says_when_every_input_failed(project: Path) -> None:
    echoed = _run_and_save(project, ["Fail    boom", ".save session.robot"])

    assert not (project / "session.robot").exists()
    assert any("every recorded input failed" in message for message in echoed)


@pytest.mark.parametrize(
    ("statement", "exported"),
    [
        pytest.param(["Skip    not now"], False, id="skip"),
        pytest.param(["Pass Execution    done"], True, id="pass-execution"),
        pytest.param(
            [
                "IF    True",
                "    Run Keyword And Continue On Failure    Fail    early",
                "    Pass Execution    done",
                "END",
            ],
            False,
            id="continued-failure-before-pass-execution",
        ),
    ],
)
def test_save_counts_skip_as_failed_and_pass_execution_as_passed(
    project: Path, statement: List[str], exported: bool
) -> None:
    _run_and_save(project, [*statement, "Log    after", ".save session.robot"])

    content = (project / "session.robot").read_text(encoding="utf-8")
    assert "Log    after" in content
    assert (statement[0] in content) is exported


# ---------------------------------------------------------------------------
# prompt_toolkit backend
# ---------------------------------------------------------------------------


@pytest.fixture
def pipe_input() -> Iterator[PipeInput]:
    with create_pipe_input() as inp:
        with create_app_session(input=inp, output=DummyOutput()):
            yield inp


def test_prompt_toolkit_runs_a_submitted_invalid_block_at_once(
    pipe_input: PipeInput, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The prompts `get_input` asks for are the ones of a terminal session.
    monkeypatch.setattr(sys, "stdin", _Stdin(tty=True))
    interp = PromptToolkitConsoleInterpreter(app=None, no_history=True)
    prompts: List[Tuple[str, str, bool]] = []
    read_line = interp.read_line

    def recording_read_line(
        prompt: str, *, multiline_continuation: bool = False, prefill: str = "", completer: Any = None
    ) -> str:
        prompts.append((prompt, prefill, multiline_continuation))
        return read_line(prompt, multiline_continuation=multiline_continuation, prefill=prefill, completer=completer)

    interp.read_line = recording_read_line  # type: ignore[method-assign]

    # Alt-Enter (`\x1b\r`) inserts a newline; Enter submits the balanced buffer.
    pipe_input.send_text("IF    True\x1b\rLog    a\x1b\rELSE\x1b\rEND\r")
    assert [type(item).__name__ for item in interp.get_input()] == ["If"]

    pipe_input.send_text("Log    next\r")
    assert [item.name for item in interp.get_input() if item is not None] == ["Log"]
    # Both inputs start at the primary prompt, without a continuation prefill.
    assert prompts == [(">>> ", "", False), (">>> ", "", False)]
