import io
import os
from pathlib import Path
from typing import Any, List

import robot

from robotcode.debugger.dap_types import Event, OutputEvent, Source, SourceBreakpoint, StoppedEvent
from robotcode.debugger.debugger import Debugger

SUITE = """\
*** Test Cases ***
T
    FOR    ${i}    IN RANGE    3
        Log    ${i}
    END
"""


def _run_with_breakpoint(tmp_path: Path, condition: str) -> List[Event]:
    suite = tmp_path / "suite.robot"
    suite.write_text(SUITE, encoding="utf-8")
    source = Source(path=str(suite))
    events: List[Event] = []

    def collect(sender: Any, event: Event) -> None:
        events.append(event)

    debugger = Debugger.instance
    debugger.send_event.add(collect)
    debugger.set_breakpoints(source, [SourceBreakpoint(line=4, condition=condition)])
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
    return events


def test_condition_error_is_reported_in_the_debug_console(tmp_path: Path) -> None:
    """A condition that raises doesn't stop, but each hit says why."""
    events = _run_with_breakpoint(tmp_path, "${nonexistent} == 1")

    assert not [e for e in events if isinstance(e, StoppedEvent)]
    errors = [
        e.body.output
        for e in events
        if isinstance(e, OutputEvent) and e.body is not None and e.body.output.startswith("Breakpoint condition error")
    ]
    assert errors == [f"Breakpoint condition error: Variable '${{nonexistent}}' not found.{os.linesep}"] * 3
