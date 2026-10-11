from pathlib import Path
from typing import Any, List

from robot import result, running

from robotcode.core.utils.path import normalized_path
from robotcode.debugger.dap_types import Event
from robotcode.debugger.debugger import Debugger
from robotcode.debugger.listeners import ListenerV3, RobotExecutionEventBody


def test_set_failed_ids_use_the_normalized_source(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    source = tmp_path / "sub" / ".." / "suite.robot"

    suite_data = running.TestSuite(name="Suite", source=str(source))
    suite_data.tests.create(name="First", lineno=5)
    suite_data.tests.create(name="Second", lineno=8)
    suite_data.teardown.config(name="Fail", args=("teardown broke",))

    suite_result = result.TestSuite(name="Suite", source=str(source))
    message = "Parent suite teardown failed:\nteardown broke"
    for test in suite_data.tests:
        suite_result.tests.create(name=test.name, status="FAIL", message=message)
    suite_result.teardown.config(status="FAIL")

    events: List[Event] = []

    def collect(sender: Any, event: Event) -> None:
        events.append(event)

    Debugger.instance.send_event.add(collect)
    try:
        ListenerV3().end_suite(suite_data, suite_result)
    finally:
        Debugger.instance.send_event.remove(collect)

    # the ids of robotStarted and robotEnded, as ListenerV2 builds them for the same tests
    expected = [f"{normalized_path(source)};Suite.First;5", f"{normalized_path(source)};Suite.Second;8"]
    bodies = [e.body for e in events if e.event == "robotSetFailed"]
    assert [b.id for b in bodies if isinstance(b, RobotExecutionEventBody)] == expected
