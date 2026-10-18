import io
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple, Union

import pytest
import robot

from robotcode.debugger.dap_types import (
    Event,
    ExceptionBreakMode,
    ExceptionFilterOptions,
    ExceptionInfoResponseBody,
    Source,
    SourceBreakpoint,
    StoppedEvent,
    StoppedReason,
)
from robotcode.debugger.debugger import Debugger
from robotcode.debugger.default_capabilities import DFEAULT_CAPABILITIES

SUITE = """\
*** Settings ***
Library    MyLib.py

*** Test Cases ***
Compare
    My Failing Keyword

In Python
    Fail In Python

*** Keywords ***
My Failing Keyword
    Should Be Equal    1    2
"""

# the test fails with the messages of both failures
COLLECTING_SUITE = """\
*** Settings ***
Library    MyLib.py

*** Test Cases ***
Collects
    Run Keyword And Continue On Failure    Fail In Python
    Run Keyword And Continue On Failure    Fail In Python
"""

LIBRARY = """\
def fail_in_python():
    int("x")
"""

VALUE_ERROR = "ValueError: invalid literal for int() with base 10: 'x'"

Stop = Tuple[StoppedEvent, Union[ExceptionInfoResponseBody, RuntimeError]]


def _run(
    tmp_path: Path,
    filter_ids: Sequence[str],
    breakpoints: Sequence[SourceBreakpoint] = (),
    suite_text: str = SUITE,
) -> List[Stop]:
    """Runs `suite_text` with the exception filters `filter_ids` and `breakpoints`.

    At each stop the client asks for the exception information and continues; each stop comes with the answer or
    the error of the request.
    """
    (tmp_path / "MyLib.py").write_text(LIBRARY, encoding="utf-8")
    suite = tmp_path / "suite.robot"
    suite.write_text(suite_text, encoding="utf-8")
    source = Source(path=str(suite))
    stops: List[Stop] = []
    debugger = Debugger.instance

    def collect(sender: Any, event: Event) -> None:
        if not isinstance(event, StoppedEvent):
            return
        try:
            stops.append((event, debugger.get_exception_info(debugger.main_thread_id)))
        except RuntimeError as e:
            stops.append((event, e))
        finally:
            debugger.continue_thread(debugger.main_thread_id)

    found = set(debugger.exception_breakpoints)
    debugger.set_exception_breakpoints([], [ExceptionFilterOptions(filter_id=f) for f in filter_ids])
    debugger.set_breakpoints(source, list(breakpoints))
    debugger.send_event.add(collect)
    # only with a client attached does the run wait at a stop until the client continues it
    debugger.attached = True
    # Robot Framework drops the debugger's logger when a run ends; the first suite of this run registers it again
    debugger.run_started = False
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
        debugger.attached = False
        debugger.set_breakpoints(source, [])
        debugger.send_event.remove(collect)
        # the singleton keeps them for the following tests
        debugger.exception_breakpoints.clear()
        debugger.exception_breakpoints.update(found)
    return stops


def _answers(stops: List[Stop]) -> List[Tuple[str, Optional[str], ExceptionBreakMode]]:
    return [
        (answer.exception_id, answer.description, answer.break_mode)
        for _, answer in stops
        if isinstance(answer, ExceptionInfoResponseBody)
    ]


def _stack_trace(stop: Stop) -> str:
    answer = stop[1]
    assert isinstance(answer, ExceptionInfoResponseBody)
    assert answer.details is not None
    assert answer.details.stack_trace is not None
    return answer.details.stack_trace


def _suite_path(tmp_path: Path, stack_trace: str) -> str:
    """The path of the suite file as the first line of `stack_trace` spells it, checked to be absolute."""
    path = stack_trace.splitlines()[0].split("  ", 1)[1].strip().rsplit(":", 1)[0]
    assert Path(path).is_absolute()
    assert Path(path).samefile(tmp_path / "suite.robot")
    return path


def test_the_capability_is_advertised() -> None:
    assert DFEAULT_CAPABILITIES.supports_exception_info_request is True


def test_each_stop_of_uncaught_failed_keywords_names_the_failed_keyword(tmp_path: Path) -> None:
    """`Should Be Equal` stops the run, its user keyword one level up again, then the keyword of the library."""
    stops = _run(tmp_path, ["uncaught_failed_keyword"])

    assert _answers(stops) == [
        ("BuiltIn.Should Be Equal", "1 != 2", ExceptionBreakMode.UNHANDLED),
        ("My Failing Keyword", "1 != 2", ExceptionBreakMode.UNHANDLED),
        ("MyLib.Fail In Python", VALUE_ERROR, ExceptionBreakMode.UNHANDLED),
    ]


@pytest.mark.parametrize(
    ("filter_ids", "break_mode"),
    [
        (["failed_keyword"], ExceptionBreakMode.ALWAYS),
        (["failed_keyword", "uncaught_failed_keyword"], ExceptionBreakMode.UNHANDLED),
    ],
    ids=["failed keywords", "both"],
)
def test_the_break_mode_follows_the_filter_that_stopped_the_run(
    tmp_path: Path, filter_ids: List[str], break_mode: ExceptionBreakMode
) -> None:
    stops = _run(tmp_path, filter_ids)

    assert [mode for _, _, mode in _answers(stops)] == [break_mode] * 3


def test_a_failed_test_is_named_with_its_message(tmp_path: Path) -> None:
    stops = _run(tmp_path, ["failed_test"])

    assert _answers(stops) == [
        ("Compare", "1 != 2", ExceptionBreakMode.ALWAYS),
        ("In Python", VALUE_ERROR, ExceptionBreakMode.ALWAYS),
    ]


def test_a_failed_suite_is_named(tmp_path: Path) -> None:
    stops = _run(tmp_path, ["failed_suite"])

    assert [(exception_id, mode) for exception_id, _, mode in _answers(stops)] == [("Suite", ExceptionBreakMode.ALWAYS)]


def test_a_stop_at_a_breakpoint_after_a_failure_has_no_exception_information(tmp_path: Path) -> None:
    stops = _run(tmp_path, ["uncaught_failed_keyword"], [SourceBreakpoint(line=9)])

    assert [(event.body.reason, isinstance(answer, RuntimeError)) for event, answer in stops] == [
        (StoppedReason.EXCEPTION, False),
        (StoppedReason.EXCEPTION, False),
        (StoppedReason.BREAKPOINT, True),
        (StoppedReason.EXCEPTION, False),
    ]


def test_the_stopped_event_keeps_its_description_and_text(tmp_path: Path) -> None:
    stops = _run(tmp_path, ["uncaught_failed_keyword"])

    body = stops[0][0].body
    assert (body.reason, body.description, body.text) == (
        StoppedReason.EXCEPTION,
        "Keyword failed.",
        "Keyword failed: 1 != 2",
    )


def test_the_stack_trace_lists_the_calls_that_led_to_the_failure(tmp_path: Path) -> None:
    """Newest first, one line per element with its absolute path and line, without the suite.

    There is no traceback, since Robot Framework leaves its own code out of tracebacks and logs `None` for
    `Should Be Equal`.
    """
    stops = _run(tmp_path, ["uncaught_failed_keyword"])

    stack_trace = _stack_trace(stops[0])
    path = _suite_path(tmp_path, stack_trace)
    assert stack_trace == f"My Failing Keyword  {path}:13\nSuite.Compare       {path}:6"


def test_one_keyword_level_up_the_stack_trace_starts_at_the_test(tmp_path: Path) -> None:
    stops = _run(tmp_path, ["uncaught_failed_keyword"])

    stack_trace = _stack_trace(stops[1])
    assert stack_trace == f"Suite.Compare  {_suite_path(tmp_path, stack_trace)}:6"


def test_a_failure_in_python_code_ends_the_stack_trace_with_its_traceback(tmp_path: Path) -> None:
    """Robot Framework logs the traceback at DEBUG, the run logs at the default level INFO."""
    stops = _run(tmp_path, ["uncaught_failed_keyword"])

    stack_trace = _stack_trace(stops[2])
    calls, traceback = stack_trace.split("\n\n", 1)
    assert calls == f"Suite.In Python  {_suite_path(tmp_path, stack_trace)}:9"
    assert traceback.startswith("Traceback (most recent call last):\n")
    assert 'MyLib.py", line 2, in fail_in_python' in traceback


def test_a_stop_at_the_end_of_a_test_shows_the_line_of_its_name(tmp_path: Path) -> None:
    """The test that failed with the message of the Python failure also shows its traceback."""
    stops = _run(tmp_path, ["failed_test"])

    compare = _stack_trace(stops[0])
    assert compare == f"Suite.Compare  {_suite_path(tmp_path, compare)}:5"
    in_python = _stack_trace(stops[1])
    assert in_python.startswith(
        f"Suite.In Python  {_suite_path(tmp_path, in_python)}:8\n\nTraceback (most recent call last):\n"
    )


def test_a_stop_at_a_failed_suite_has_no_details(tmp_path: Path) -> None:
    stops = _run(tmp_path, ["failed_suite"])

    answer = stops[0][1]
    assert isinstance(answer, ExceptionInfoResponseBody)
    assert answer.details is None


def test_a_stop_whose_message_is_not_the_last_failure_has_no_traceback(tmp_path: Path) -> None:
    stops = _run(tmp_path, ["failed_test"], suite_text=COLLECTING_SUITE)

    stack_trace = _stack_trace(stops[0])
    assert stack_trace == f"Suite.Collects  {_suite_path(tmp_path, stack_trace)}:5"
