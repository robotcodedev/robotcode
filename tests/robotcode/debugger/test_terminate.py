import io
import os
import threading
from pathlib import Path
from typing import Any, Callable, List, Optional

import pytest
import robot

from robotcode.debugger.dap_types import (
    Event,
    ExceptionFilterOptions,
    OutputEvent,
    Source,
    SourceBreakpoint,
    StoppedEvent,
)
from robotcode.debugger.debugger import Debugger, RequestedState, State

SUITE = """\
*** Test Cases ***
T
    Log    body
    Log    after
    [Teardown]    Log    in teardown
"""

# a stop in `Inner` can step over, into and out of a keyword
NESTED_SUITE = """\
*** Test Cases ***
T
    Inner
    Log    after
    [Teardown]    Log    in teardown

*** Keywords ***
Inner
    Log    inside
    Log    inside again
"""

FAILING_SUITE = """\
*** Test Cases ***
T
    Log    body
    Fail    boom
    [Teardown]    Log    in teardown
"""


def _run(
    tmp_path: Path,
    breakpoints: List[SourceBreakpoint],
    after_terminate: Optional[Callable[[Debugger], None]] = None,
    suite_text: str = SUITE,
    stop_on_entry: bool = False,
) -> List[Event]:
    """Runs the suite with `breakpoints`; at the first stop the client asks to terminate, then `after_terminate` runs.

    The run goes on without a signal, because only the `terminate` request of the server raises one. With
    `stop_on_entry`, the client has asked to terminate before the run starts.
    """
    suite = tmp_path / "suite.robot"
    suite.write_text(suite_text, encoding="utf-8")
    source = Source(path=str(suite))
    events: List[Event] = []
    debugger = Debugger.instance

    def collect(sender: Any, event: Event) -> None:
        events.append(event)
        if isinstance(event, StoppedEvent) and not debugger.terminated:
            debugger.terminate()
            if after_terminate is not None:
                after_terminate(debugger)

    debugger.send_event.add(collect)
    debugger.set_breakpoints(source, breakpoints)
    if stop_on_entry:
        debugger.stop_on_entry = True
        debugger.terminate()
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
        debugger.set_breakpoints(source, [])
        debugger.send_event.remove(collect)
        # the singleton keeps both for the following tests
        debugger.terminated = False
        debugger.stop_on_entry = False
    return events


def _stops(events: List[Event]) -> List[StoppedEvent]:
    return [e for e in events if isinstance(e, StoppedEvent)]


def _console(events: List[Event]) -> List[str]:
    return [e.body.output for e in events if isinstance(e, OutputEvent) and e.body is not None]


def test_no_pause_at_breakpoints_after_terminate(tmp_path: Path) -> None:
    """Stopped in the test body, the run passes the breakpoints after it and in the teardown."""
    events = _run(tmp_path, [SourceBreakpoint(line=3), SourceBreakpoint(line=4), SourceBreakpoint(line=5)])

    assert len(_stops(events)) == 1


def test_log_message_in_the_teardown_is_written_after_terminate(tmp_path: Path) -> None:
    events = _run(tmp_path, [SourceBreakpoint(line=3), SourceBreakpoint(line=5, log_message="teardown reached")])

    assert len(_stops(events)) == 1
    assert f"teardown reached{os.linesep}" in _console(events)


def test_no_condition_error_after_terminate(tmp_path: Path) -> None:
    """A breakpoint that can no longer pause is not evaluated, so its failing condition reports nothing."""
    events = _run(tmp_path, [SourceBreakpoint(line=3), SourceBreakpoint(line=5, condition="${nonexistent} == 1")])

    assert len(_stops(events)) == 1
    assert [o for o in _console(events) if o.startswith("Breakpoint condition error")] == []


@pytest.mark.parametrize(
    "request_after_terminate",
    [
        lambda d: d.next(d.main_thread_id),
        lambda d: d.step_in(d.main_thread_id),
        lambda d: d.step_out(d.main_thread_id),
        lambda d: d.pause_thread(0),
    ],
    ids=["next", "stepIn", "stepOut", "pause"],
)
def test_no_pause_for_a_step_or_pause_request_after_terminate(
    tmp_path: Path, request_after_terminate: Callable[[Debugger], None]
) -> None:
    events = _run(
        tmp_path, [SourceBreakpoint(line=9)], after_terminate=request_after_terminate, suite_text=NESTED_SUITE
    )

    assert len(_stops(events)) == 1


def test_no_pause_on_entry_after_terminate(tmp_path: Path) -> None:
    events = _run(tmp_path, [], stop_on_entry=True)

    assert _stops(events) == []


def test_no_pause_at_a_failed_keyword_after_terminate(tmp_path: Path) -> None:
    debugger = Debugger.instance
    found = set(debugger.exception_breakpoints)
    debugger.set_exception_breakpoints([], [ExceptionFilterOptions(filter_id="failed_keyword")])
    try:
        events = _run(tmp_path, [SourceBreakpoint(line=3)], suite_text=FAILING_SUITE)
    finally:
        debugger.exception_breakpoints.clear()
        debugger.exception_breakpoints.update(found)

    assert len(_stops(events)) == 1


def test_a_pause_that_began_as_terminate_arrived_ends_at_once() -> None:
    """The run paused just after it had checked for a terminate request, so nothing continued it."""
    debugger = Debugger.instance
    debugger.attached = True
    debugger.state = State.Paused
    waiting = threading.Thread(target=debugger.wait_for_running, daemon=True)
    try:
        debugger.terminate()
        waiting.start()
        waiting.join(5)

        assert not waiting.is_alive()
        assert debugger.state == State.Running
    finally:
        # releases a wait that did not end, so that a failing run of this test does not hang
        with debugger.condition:
            debugger.requested_state = RequestedState.Running
            debugger.condition.notify_all()
        waiting.join(5)
        debugger.attached = False
        debugger.terminated = False
        debugger.requested_state = RequestedState.Nothing
        debugger.state = State.Stopped
