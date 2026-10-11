import io
import os
from pathlib import Path
from typing import Any, List, Tuple

import pytest
import robot
from robot.running import EXECUTION_CONTEXTS

from robotcode.debugger.dap_types import Event, OutputEvent, Source, SourceBreakpoint, StoppedEvent
from robotcode.debugger.debugger import Debugger

SUITE = """\
*** Test Cases ***
T
    FOR    ${i}    IN RANGE    3
        Log    ${i}
    END
"""


def _run_with_breakpoint(tmp_path: Path, breakpoint: SourceBreakpoint) -> Tuple[List[Event], List[int]]:
    """Runs SUITE with `breakpoint`; returns the debugger's events and the `${i}` of every stop."""
    suite = tmp_path / "suite.robot"
    suite.write_text(SUITE, encoding="utf-8")
    source = Source(path=str(suite))
    events: List[Event] = []
    stopped_at: List[int] = []

    def collect(sender: Any, event: Event) -> None:
        events.append(event)
        if isinstance(event, StoppedEvent):
            stopped_at.append(EXECUTION_CONTEXTS.current.variables["${i}"])

    debugger = Debugger.instance
    debugger.send_event.add(collect)
    debugger.set_breakpoints(source, [breakpoint])
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
    return events, stopped_at


def _console_errors(events: List[Event], prefix: str) -> List[str]:
    return [
        e.body.output
        for e in events
        if isinstance(e, OutputEvent) and e.body is not None and e.body.output.startswith(prefix)
    ]


def test_condition_error_is_reported_in_the_debug_console(tmp_path: Path) -> None:
    """A condition that raises doesn't stop, but each hit says why."""
    events, stopped_at = _run_with_breakpoint(tmp_path, SourceBreakpoint(line=4, condition="${nonexistent} == 1"))

    assert stopped_at == []
    assert (
        _console_errors(events, "Breakpoint condition error")
        == [f"Breakpoint condition error: Variable '${{nonexistent}}' not found.{os.linesep}"] * 3
    )


@pytest.mark.parametrize(
    ("hit_condition", "expected"),
    [("2", [1]), ("== 2", [1]), (">= 2", [1, 2]), ("> 1", [1, 2]), ("< 3", [0, 1]), ("% 2", [1])],
)
def test_hit_count_stops_at_the_matching_hits(tmp_path: Path, hit_condition: str, expected: List[int]) -> None:
    """The loop runs with `${i}` 0, 1, 2, so the second hit is `${i}` 1."""
    _, stopped_at = _run_with_breakpoint(tmp_path, SourceBreakpoint(line=4, hit_condition=hit_condition))

    assert stopped_at == expected


def test_invalid_hit_count_is_reported_in_the_debug_console(tmp_path: Path) -> None:
    events, stopped_at = _run_with_breakpoint(tmp_path, SourceBreakpoint(line=4, hit_condition="abc"))

    error = "Breakpoint hit count error: 'abc' is not a valid hit count; use N, == N, > N, >= N, < N, <= N or % N."
    assert stopped_at == []
    assert _console_errors(events, "Breakpoint hit count error") == [error + os.linesep] * 3
