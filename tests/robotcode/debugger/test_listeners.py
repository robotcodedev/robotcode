import io
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, TypeVar

import pytest
import robot
from click.testing import CliRunner
from robot import result, running

from robotcode.cli import robotcode
from robotcode.core.utils.path import normalized_path
from robotcode.debugger.dap_types import Event
from robotcode.debugger.debugger import Debugger
from robotcode.debugger.listeners import (
    ListenerV3,
    RobotEnqueuedEventBody,
    RobotExecutionEventBody,
    RobotLogMessageEventBody,
)
from robotcode.robot.utils import get_robot_version

T = TypeVar("T")


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


def _ended(tmp_path: Path, files: Dict[str, str]) -> List[RobotExecutionEventBody]:
    """Runs `suite.robot` of `files`, written to `tmp_path`, and returns the bodies of its `robotEnded` events."""
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    events: List[Event] = []

    def collect(sender: Any, event: Event) -> None:
        events.append(event)

    debugger = Debugger.instance
    debugger.send_event.add(collect)
    debugger.start()
    try:
        robot.run(
            str(tmp_path / "suite.robot"),
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

    return [e.body for e in events if e.event == "robotEnded" and isinstance(e.body, RobotExecutionEventBody)]


def test_failed_keywords_mark_the_failures_that_were_caught(tmp_path: Path) -> None:
    ended = _ended(tmp_path, {"suite.robot": CAUGHT_SUITE})

    # a keyword that a Run Keyword variant runs has no source before Robot Framework 6.1, so the listener, which keeps
    # failed keywords with a source only, does not have it
    def wrapped(name: str, line: int) -> List[Any]:
        return [(name, line, True)] if get_robot_version() >= (6, 1) else []

    # newest first, as the listener sends them; marked are the failures that Robot Framework's log keeps collapsed,
    # also the TRY branch's after a failing EXCEPT or FINALLY branch is not, as the log expands it then
    failed = {
        body.name: [(k["kwname"], k["lineno"], k.get("caught", False)) for k in body.failed_keywords or []]
        for body in ended
        if body.type == "test"
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


# failures nested in a resource file, collected in different ways, in a TRY and its EXCEPT branch, caught, with the
# same text, and collected by one keyword; the suite teardown fails as well
FAILURES_SUITE = """\
*** Settings ***
Resource    shop.resource
Suite Teardown    Check Value    10

*** Test Cases ***
Nested
    Outer In Resource

Continue On Failure
    Run Keyword And Continue On Failure    Check Value    1
    Run Keyword And Continue On Failure    Check Value    2

Tagged Continue
    [Tags]    robot:continue-on-failure
    Check Value    3
    Check Value    4

Body And Teardown
    Check Value    5
    [Teardown]    Check Value    6

Failing Except
    TRY
        Should Be Equal    a    b
    EXCEPT
        Check Value    7
    END

Caught Then Failed
    Run Keyword And Ignore Error    Check Value    8
    Check Value    9

Same Text Twice
    Run Keyword And Continue On Failure    Should Be Equal    x    y
    Run Keyword And Continue On Failure    Should Be Equal    x    y

Keyword Collects Two
    Collect Two

*** Keywords ***
Collect Two
    [Tags]    robot:continue-on-failure
    Should Be Equal    c    d
    Should Be Equal    e    f
"""

SHOP_RESOURCE = """\
*** Keywords ***
Outer In Resource
    Inner In Resource

Inner In Resource
    Check Value    0

Check Value
    [Arguments]    ${v}
    Should Be Equal    ${v}    ok

Retry Check
    Wait Until Keyword Succeeds    2x    10ms    Check Value    1
"""


def _describe(keyword: Dict[str, Any]) -> str:
    return f"{keyword['kwname']} {Path(keyword['source']).name}:{keyword['lineno']}" + (
        " caught" if keyword.get("caught") else ""
    )


def _failures(body: RobotExecutionEventBody) -> List[Tuple[str, List[str]]]:
    """Each failure of `body` as the failed keyword whose message is the failure's, and its calls, innermost first."""
    keywords = body.failed_keywords or []
    return [(_describe(keywords[f.keyword]), [_describe(keywords[i]) for i in f.calls]) for f in body.failures or []]


def _since_rf61(*items: T) -> List[T]:
    """Calls of keywords that a Run Keyword variant runs: before Robot Framework 6.1 they have no source, so the
    listener, which keeps failed keywords with a source only, does not have them."""
    return list(items) if get_robot_version() >= (6, 1) else []


def test_each_failure_lists_its_failed_keywords_innermost_first(tmp_path: Path) -> None:
    ended = _ended(tmp_path, {"suite.robot": FAILURES_SUITE, "shop.resource": SHOP_RESOURCE})
    failures = {body.name: _failures(body) for body in ended}

    # none of these keywords turns the failures inside it into its own, so each failure is its innermost call
    assert all(keyword == calls[0] for name in failures for keyword, calls in failures[name])
    # the call of Should Be Equal in Check Value
    comparison = "Should Be Equal shop.resource:10"
    continued = "Run Keyword And Continue On Failure"
    # in the order the failures occurred; a keyword that collected several failures is in each of them
    assert {name: [calls for _, calls in f] for name, f in failures.items()} == {
        "Nested": [
            [
                comparison,
                "Check Value shop.resource:6",
                "Inner In Resource shop.resource:3",
                "Outer In Resource suite.robot:7",
            ]
        ],
        "Continue On Failure": [
            [comparison, *_since_rf61("Check Value suite.robot:10"), f"{continued} suite.robot:10"],
            [comparison, *_since_rf61("Check Value suite.robot:11"), f"{continued} suite.robot:11"],
        ],
        "Tagged Continue": [
            [comparison, "Check Value suite.robot:15"],
            [comparison, "Check Value suite.robot:16"],
        ],
        "Body And Teardown": [
            [comparison, "Check Value suite.robot:19"],
            [comparison, "Check Value suite.robot:20"],
        ],
        "Failing Except": [
            ["Should Be Equal suite.robot:24"],
            [comparison, "Check Value suite.robot:26"],
        ],
        "Caught Then Failed": [
            [f"{comparison} caught", *_since_rf61("Check Value suite.robot:30 caught")],
            [comparison, "Check Value suite.robot:31"],
        ],
        "Same Text Twice": [
            [*_since_rf61("Should Be Equal suite.robot:34"), f"{continued} suite.robot:34"],
            [*_since_rf61("Should Be Equal suite.robot:35"), f"{continued} suite.robot:35"],
        ],
        "Keyword Collects Two": [
            ["Should Be Equal suite.robot:43", "Collect Two suite.robot:38"],
            ["Should Be Equal suite.robot:44", "Collect Two suite.robot:38"],
        ],
        "Suite": [[comparison, "Check Value suite.robot:3"]],
    }


# keywords that turn the failures inside them into their own: after the last attempt, with another error than the one
# expected, in a keyword of a resource file, and inside a keyword that caught it; and a retried keyword that passed
# after a failed attempt, in a test that fails later
WRAPPERS_SUITE = """\
*** Settings ***
Resource    shop.resource

*** Test Cases ***
Retries Fail
    Wait Until Keyword Succeeds    3x    10ms    Should Be Equal    a    b

Expect Other Error
    Run Keyword And Expect Error    Wrong*    Should Be Equal    a    b

Retries In Keyword
    Retry Check

Retried Until Passed
    Wait Until Keyword Succeeds    3x    10ms    Flaky
    Should Be Equal    x    y

Ignored Retries
    Run Keyword And Ignore Error    Wait Until Keyword Succeeds    2x    10ms    Should Be Equal    c    d
    Fail    later

*** Keywords ***
Flaky
    ${n}=    Get Variable Value    ${FLAKY_N}    ${0}
    Set Suite Variable    ${FLAKY_N}    ${n + 1}
    Should Be True    ${n} >= 1
"""


def test_a_keyword_that_turns_failures_into_its_own_is_one_failure(tmp_path: Path) -> None:
    ended = [body for body in _ended(tmp_path, {"suite.robot": WRAPPERS_SUITE, "shop.resource": SHOP_RESOURCE})]
    tests = {body.name: body for body in ended if body.type == "test"}

    retried = "Wait Until Keyword Succeeds"
    expected = "Run Keyword And Expect Error"
    # its calls start with the last attempt
    assert {name: _failures(body) for name, body in tests.items()} == {
        "Retries Fail": [
            (f"{retried} suite.robot:6", [*_since_rf61("Should Be Equal suite.robot:6"), f"{retried} suite.robot:6"])
        ],
        "Expect Other Error": [
            (f"{expected} suite.robot:9", [*_since_rf61("Should Be Equal suite.robot:9"), f"{expected} suite.robot:9"])
        ],
        "Retries In Keyword": [
            (
                f"{retried} shop.resource:13",
                [
                    "Should Be Equal shop.resource:10",
                    *_since_rf61("Check Value shop.resource:13"),
                    f"{retried} shop.resource:13",
                    "Retry Check suite.robot:12",
                ],
            )
        ],
        "Retried Until Passed": [
            (
                "Should Be True suite.robot:26 caught",
                ["Should Be True suite.robot:26 caught", *_since_rf61("Flaky suite.robot:15 caught")],
            ),
            ("Should Be Equal suite.robot:16", ["Should Be Equal suite.robot:16"]),
        ],
        "Ignored Retries": [
            *_since_rf61(
                (
                    f"{retried} suite.robot:19 caught",
                    ["Should Be Equal suite.robot:19 caught", f"{retried} suite.robot:19 caught"],
                )
            ),
            ("Fail suite.robot:20", ["Fail suite.robot:20"]),
        ],
    }

    # the failure carries the message the test failed with
    for name in ["Retries Fail", "Expect Other Error", "Retries In Keyword"]:
        body = tests[name]
        assert body.failures is not None
        assert body.failed_keywords is not None
        assert body.attributes is not None
        assert body.failed_keywords[body.failures[0].keyword]["message"] == body.attributes["message"]


# keywords that fail and then catch a failure, in their teardown or in a later step under robot:continue-on-failure:
# the caught failure is logged last, but neither keyword turns the failures before it into one of its own
CAUGHT_LATER_SUITE = """\
*** Test Cases ***
Teardown With Caught Failure
    Keyword With Cleanup

Collector Then Caught
    Collect And Ignore

*** Keywords ***
Keyword With Cleanup
    Should Be Equal    a    b
    [Teardown]    Run Keyword And Ignore Error    Fail    cleanup failed

Collect And Ignore
    [Tags]    robot:continue-on-failure
    Should Be Equal    c    d
    Should Be Equal    e    f
    Run Keyword And Ignore Error    Fail    ignored
"""


def test_a_failure_caught_later_keeps_the_failures_before_it(tmp_path: Path) -> None:
    ended = _ended(tmp_path, {"suite.robot": CAUGHT_LATER_SUITE})

    cleanup = "Keyword With Cleanup suite.robot:3"
    collector = "Collect And Ignore suite.robot:6"
    assert {body.name: _failures(body) for body in ended if body.type == "test"} == {
        "Teardown With Caught Failure": [
            ("Should Be Equal suite.robot:10", ["Should Be Equal suite.robot:10", cleanup]),
            *_since_rf61(("Fail suite.robot:11 caught", ["Fail suite.robot:11 caught", cleanup])),
        ],
        "Collector Then Caught": [
            ("Should Be Equal suite.robot:15", ["Should Be Equal suite.robot:15", collector]),
            ("Should Be Equal suite.robot:16", ["Should Be Equal suite.robot:16", collector]),
            *_since_rf61(("Fail suite.robot:17 caught", ["Fail suite.robot:17 caught", collector])),
        ],
    }


def test_set_failed_ids_of_tests_without_a_line_end_in_0(tmp_path: Path) -> None:
    source = tmp_path / "suite.robot"

    # as a custom parser or a pre-run modifier creates them
    suite_data = running.TestSuite(name="Suite", source=str(source))
    suite_data.tests.create(name="First")
    suite_data.tests.create(name="Second")
    suite_data.teardown.config(name="Fail", args=("teardown broke",))

    suite_result = result.TestSuite(name="Suite", source=str(source))
    for test in suite_data.tests:
        suite_result.tests.create(
            name=test.name, status="FAIL", message="Parent suite teardown failed:\nteardown broke"
        )
    suite_result.teardown.config(status="FAIL")

    events: List[Event] = []

    def collect(sender: Any, event: Event) -> None:
        events.append(event)

    Debugger.instance.send_event.add(collect)
    try:
        ListenerV3().end_suite(suite_data, suite_result)
    finally:
        Debugger.instance.send_event.remove(collect)

    bodies = [e.body for e in events if e.event == "robotSetFailed" and isinstance(e.body, RobotExecutionEventBody)]
    assert [b.id for b in bodies] == [
        f"{normalized_path(source)};Suite.First;0",
        f"{normalized_path(source)};Suite.Second;0",
    ]


def _discovered_tests(root: Path, *args: str) -> Dict[str, str]:
    """The IDs of the tests that `robotcode discover all` reports, by name."""
    options = ["--no-color", "--no-pager", "--root", str(root), "--format", "json"]
    discovery = CliRunner().invoke(robotcode, [*options, "discover", "--no-diagnostics", "all", *args])
    assert discovery.exit_code == 0, discovery.output

    def tests(item: Dict[str, Any]) -> List[Dict[str, Any]]:
        own = [item] if item["type"] == "test" else []
        return own + [test for child in item.get("children") or [] for test in tests(child)]

    return {test["name"]: test["id"] for test in tests(json.loads(discovery.stdout)["items"][0])}


def _run_events(source: Path, **options: Any) -> List[Event]:
    """Runs `source` with the debugger's listeners and returns the events they send."""
    events: List[Event] = []

    def collect(sender: Any, event: Event) -> None:
        events.append(event)

    debugger = Debugger.instance
    debugger.send_event.add(collect)
    debugger.start()
    try:
        robot.run(
            str(source),
            listener=["robotcode.debugger.listeners.ListenerV3", "robotcode.debugger.listeners.ListenerV2"],
            output="NONE",
            log="NONE",
            report="NONE",
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            **options,
        )
    finally:
        debugger.stop()
        debugger.send_event.remove(collect)
    return events


def _test_bodies(events: List[Event], event_name: str) -> List[RobotExecutionEventBody]:
    return [
        e.body
        for e in events
        if e.event == event_name and isinstance(e.body, RobotExecutionEventBody) and e.body.type == "test"
    ]


# the class-based parser example of Robot Framework's User Guide (ParserInterface.rst), which creates its tests
# without a line number
EXAMPLE_PARSER = """\
from pathlib import Path

from robot.api import TestSuite


class ExampleParser:
    def __init__(self, extension: str):
        self.extension = extension

    def parse(self, source: Path) -> TestSuite:
        name = TestSuite.name_from_source(source, self.extension)
        suite = TestSuite(name, source=source)
        for line in source.read_text().splitlines():
            test = suite.tests.create(name=line)
            test.body.create_keyword(name="Log", args=["Hello!"])
        return suite
"""


@pytest.mark.skipif(get_robot_version() < (6, 1), reason="requires Robot Framework 6.1+ (custom parsers)")
def test_a_run_reports_tests_without_a_line_under_the_ids_of_their_discovery(tmp_path: Path) -> None:
    (tmp_path / "ExampleParser.py").write_text(EXAMPLE_PARSER, encoding="utf-8")
    suite_file = tmp_path / "example.example"
    suite_file.write_text("First Test\nSecond Test\n", encoding="utf-8")
    parser = f"{tmp_path / 'ExampleParser.py'}:example"

    discovered = list(_discovered_tests(tmp_path, "--parser", parser, str(suite_file)).values())
    assert len(discovered) == 2
    assert all(i.endswith(";0") for i in discovered)

    events = _run_events(suite_file, parser=parser)

    enqueued = [i for e in events if isinstance(e.body, RobotEnqueuedEventBody) for i in e.body.items]
    assert set(discovered) <= set(enqueued)

    for name in ("robotStarted", "robotEnded"):
        tests = _test_bodies(events, name)
        assert [b.id for b in tests] == discovered, name
        # empty on every Robot Framework version; up to 6.1, listeners get "" for it
        assert [b.lineno for b in tests] == [None, None], name
        assert [(b.attributes or {})["lineno"] for b in tests] == [None, None], name


# a pre-run modifier that adds a test without a line number, which logs a warning and then fails
ADD_WARNING_TEST = """\
from robot.api import SuiteVisitor
from robot.model import TestSuite


class AddWarningTest(SuiteVisitor):
    def start_suite(self, suite: TestSuite) -> None:
        if suite.tests:
            test = suite.tests.create(name="Added Test")
            test.body.create_keyword(name="Log", args=["careful", "WARN"])
            test.body.create_keyword(name="Fail", args=["broke"])
"""


def test_a_test_without_a_line_logs_under_the_id_of_its_discovery(tmp_path: Path) -> None:
    (tmp_path / "AddWarningTest.py").write_text(ADD_WARNING_TEST, encoding="utf-8")
    suite_file = tmp_path / "suite.robot"
    suite_file.write_text("*** Test Cases ***\nOwn Test\n    Log    own\n", encoding="utf-8")
    modifier = str(tmp_path / "AddWarningTest.py")

    added_id = _discovered_tests(tmp_path, "--prerunmodifier", modifier, str(suite_file))["Added Test"]
    assert added_id == f"{normalized_path(suite_file)};Suite.Added Test;0"

    events = _run_events(suite_file, prerunmodifier=modifier)

    warnings = [
        e.body
        for e in events
        if e.event == "robotLog" and isinstance(e.body, RobotLogMessageEventBody) and e.body.level == "WARN"
    ]
    assert [(w.item_id, w.lineno) for w in warnings] == [(added_id, None)]

    ended = [b for b in _test_bodies(events, "robotEnded") if b.name == "Added Test"]
    assert [(b.id, b.lineno, (b.attributes or {})["lineno"]) for b in ended] == [(added_id, None, None)]
    assert [keyword["lineno"] for keyword in ended[0].failed_keywords or []] == [None]
