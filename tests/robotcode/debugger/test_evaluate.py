import io
import threading
from pathlib import Path
from typing import Any, Union

import pytest
import robot
from robot.errors import ExecutionFailed

from robotcode.debugger.dap_types import (
    EvaluateArgumentContext,
    Event,
    Source,
    SourceBreakpoint,
    StoppedEvent,
)
from robotcode.debugger.debugger import Debugger
from robotcode.robot.utils import RF_VERSION

SUITE = """\
*** Test Cases ***
T
    ${x}=    Set Variable    hello
    ${n}=    Evaluate    2
    @{l}=    Create List    a    b
    ${inner}=    Set Variable    x
    ${user}=    Set Variable    alice
    ${page}=    Set Variable    home
    Log    stop here

*** Keywords ***
${who} logs in to ${where}
    RETURN    ${who} at ${where}
"""
STOP_LINE = 9


def _evaluate_at_stop(tmp_path: Path, expression: str, context: EvaluateArgumentContext) -> Union[str, Exception]:
    """Stops at `STOP_LINE` and evaluates `expression` from a second thread, as a client's request does; returns the
    result the client sees or the exception that answers the request."""
    suite = tmp_path / "suite.robot"
    suite.write_text(SUITE, encoding="utf-8")
    source = Source(path=str(suite))
    debugger = Debugger.instance
    answer: list[Union[str, Exception]] = []
    threads: list[threading.Thread] = []

    def client() -> None:
        try:
            answer.append(debugger.evaluate(expression, debugger.full_stack_frames[0].id, context).result)
        except Exception as e:
            answer.append(e)
        finally:
            debugger.continue_all()

    def on_event(sender: Any, event: Event) -> None:
        if isinstance(event, StoppedEvent):
            threads.append(threading.Thread(target=client))
            threads[-1].start()

    debugger.send_event.add(on_event)
    debugger.set_breakpoints(source, [SourceBreakpoint(line=STOP_LINE)])
    debugger.attached = True
    debugger.set_main_thread(threading.current_thread())
    debugger.start()
    try:
        robot.run(
            str(suite),
            listener=["robotcode.debugger.listeners.ListenerV3", "robotcode.debugger.listeners.ListenerV2"],
            output="NONE",
            log="NONE",
            report="NONE",
            stdout=io.StringIO(),
            stderr=io.StringIO(),
        )
    finally:
        debugger.stop()
        # the singleton keeps both for the following tests
        debugger.attached = False
        debugger.main_thread = None
        debugger.set_breakpoints(source, [])
        debugger.send_event.remove(on_event)
        for thread in threads:
            thread.join()
    assert len(answer) == 1
    return answer[0]


@pytest.mark.parametrize(
    ("expression", "result"),
    [
        ("${x}", "'hello'"),
        ("  ${x}  ", "'hello'"),
        ("@{l}", "['a', 'b']"),
        ("${l}[0]", "'a'"),
        ("${${inner}}", "'hello'"),
        ("${{1  +  1}}", "2"),
        ('${{"ich" + "bin" * 5}}', "'ichbinbinbinbinbin'"),
    ],
)
def test_debug_console_shows_the_value_of_one_variable(tmp_path: Path, expression: str, result: str) -> None:
    assert _evaluate_at_stop(tmp_path, expression, EvaluateArgumentContext.REPL) == result


def test_debug_console_runs_a_keyword_with_embedded_arguments(tmp_path: Path) -> None:
    answer = _evaluate_at_stop(tmp_path, "${user} logs in to ${page}", EvaluateArgumentContext.REPL)

    assert answer == "'alice at home'"


@pytest.mark.skipif(RF_VERSION < (6, 0), reason="Robot Framework 5.0 drops a line that is only a variable")
def test_debug_console_runs_several_lines_as_a_test_body(tmp_path: Path) -> None:
    answer = _evaluate_at_stop(tmp_path, "${x}\nSet Variable    after", EvaluateArgumentContext.REPL)

    assert isinstance(answer, ExecutionFailed)


@pytest.mark.parametrize(
    ("expression", "result"),
    [
        ("${x}", "'hello'"),
        ("${n} + ${n}", "4"),
        ("${n} + 1", "3"),
        ("${nope}", "<undefined>"),
    ],
)
def test_watch(tmp_path: Path, expression: str, result: str) -> None:
    assert _evaluate_at_stop(tmp_path, expression, EvaluateArgumentContext.WATCH) == result
