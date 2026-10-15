import io
from pathlib import Path
from typing import Any, List

import robot
from robot import result, running

from robotcode.core.utils.path import normalized_path
from robotcode.debugger.dap_types import Event
from robotcode.debugger.debugger import Debugger
from robotcode.debugger.listeners import ListenerV3, RobotExecutionEventBody
from robotcode.robot.utils import get_robot_version


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


# each test fails in `Check Value` after an earlier failure, which only the first test and the last three catch
CAUGHT_SUITE = """\
*** Test Cases ***
Caught By Try
    TRY
        Should Be Equal    a    b
    EXCEPT
        Log    caught
    END
    Check Value    1

Failing Except
    TRY
        Should Be Equal    a    b
    EXCEPT
        Check Value    2
    END

Failing Finally
    TRY
        Should Be Equal    a    b
    EXCEPT
        Log    caught
    FINALLY
        Check Value    3
    END

Ignored Error
    Run Keyword And Ignore Error    Check Value    9
    Check Value    4

Expected Error
    Run Keyword And Expect Error    *    Check Value    9
    Check Value    5

Retried
    Wait Until Keyword Succeeds    3x    10ms    Flaky
    Check Value    6

*** Keywords ***
Check Value
    [Arguments]    ${v}
    Should Be Equal    ${v}    0

Flaky
    ${n}=    Get Variable Value    ${FLAKY_N}    ${0}
    Set Suite Variable    ${FLAKY_N}    ${n + 1}
    Should Be True    ${n} >= 1
"""


def test_failed_keywords_mark_the_failures_that_were_caught(tmp_path: Path) -> None:
    suite = tmp_path / "suite.robot"
    suite.write_text(CAUGHT_SUITE, encoding="utf-8")
    events: List[Event] = []

    def collect(sender: Any, event: Event) -> None:
        events.append(event)

    debugger = Debugger.instance
    debugger.send_event.add(collect)
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
        debugger.send_event.remove(collect)

    # a keyword that a Run Keyword variant runs has no source before Robot Framework 6.1, so the listener, which keeps
    # failed keywords with a source only, does not have it
    def wrapped(name: str, line: int) -> List[Any]:
        return [(name, line, True)] if get_robot_version() >= (6, 1) else []

    # newest first, as the listener sends them; marked are the failures that Robot Framework's log keeps collapsed,
    # also the TRY branch's after a failing EXCEPT or FINALLY branch is not, as the log expands it then
    failed = {
        e.body.name: [(k["kwname"], k["lineno"], k.get("caught", False)) for k in e.body.failed_keywords or []]
        for e in events
        if e.event == "robotEnded" and isinstance(e.body, RobotExecutionEventBody) and e.body.type == "test"
    }
    assert failed == {
        "Caught By Try": [("Check Value", 8, False), ("Should Be Equal", 41, False), ("Should Be Equal", 4, True)],
        "Failing Except": [("Check Value", 14, False), ("Should Be Equal", 41, False), ("Should Be Equal", 12, False)],
        "Failing Finally": [("Check Value", 23, False), ("Should Be Equal", 41, False), ("Should Be Equal", 19, False)],
        "Ignored Error": [
            ("Check Value", 28, False),
            ("Should Be Equal", 41, False),
            *wrapped("Check Value", 27),
            ("Should Be Equal", 41, True),
        ],
        "Expected Error": [
            ("Check Value", 32, False),
            ("Should Be Equal", 41, False),
            *wrapped("Check Value", 31),
            ("Should Be Equal", 41, True),
        ],
        "Retried": [
            ("Check Value", 36, False),
            ("Should Be Equal", 41, False),
            *wrapped("Flaky", 35),
            ("Should Be True", 46, True),
        ],
    }
