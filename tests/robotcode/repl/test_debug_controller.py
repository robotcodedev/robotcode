"""Tests for the DebugController stack model (Phase 2a).

The controller is a keyword observer. Here it's driven directly by a small
LOGGER logger (version-aware, mirroring `InterpreterLogger`) running a real
in-process suite — the same mechanism the interpreter uses, minus the prompt.
"""

import io
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import pytest
from robot.api import TestSuite as _RobotSuite  # aliased so pytest doesn't try to collect it
from robot.api import get_model
from robot.output import LOGGER

from robotcode.repl._debug.controller import DebugController
from robotcode.repl._debug.types import DebugTerminated, ResumeAction, StackFrame, StopEvent, StopReason
from robotcode.repl.base_interpreter import ExecutionObserver
from robotcode.robot.utils import RF_VERSION

if TYPE_CHECKING:
    from robot import result, running

# Source path stamped onto the in-process suites so breakpoints can match by path.
_SOURCE = "/tmp/probe_suite.robot"

SUITE = """\
*** Keywords ***
Inner Keyword
    No Operation

Outer Keyword
    Inner Keyword

*** Test Cases ***
Probe Test
    Outer Keyword
    FOR    ${i}    IN RANGE    1
        IF    ${i} == 0
            No Operation
        ELSE
            Fail    not taken
        END
    END
"""


def _run_with_observers(suite_text: str, *observers: ExecutionObserver) -> None:
    """Run `suite_text` in-process, forwarding start/end keyword + body-item and
    start/end test/suite events to `observers` (in order) via a registered LOGGER."""

    def _start(data: "running.Keyword", result: "result.Keyword") -> None:
        for obs in observers:
            obs.start_keyword(data, result)

    def _end(data: "running.Keyword", result: "result.Keyword") -> None:
        for obs in observers:
            obs.end_keyword(data, result)

    def _start_test(data: Any, result: Any) -> None:
        for obs in observers:
            obs.start_test(data, result)

    def _end_test(data: Any, result: Any) -> None:
        for obs in observers:
            obs.end_test(data, result)

    def _start_suite(data: Any, result: Any) -> None:
        for obs in observers:
            obs.start_suite(data, result)

    def _end_suite(data: Any, result: Any) -> None:
        for obs in observers:
            obs.end_suite(data, result)

    if RF_VERSION >= (7, 0):
        import robot.output.loggerapi

        class _ForwardingLogger(robot.output.loggerapi.LoggerApi):
            def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
                _start(data, result)

            def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
                _end(data, result)

            def start_body_item(self, data: "running.Keyword", result: "result.Keyword") -> None:
                _start(data, result)

            def end_body_item(self, data: "running.Keyword", result: "result.Keyword") -> None:
                _end(data, result)

            def start_test(self, data: Any, result: Any) -> None:
                _start_test(data, result)

            def end_test(self, data: Any, result: Any) -> None:
                _end_test(data, result)

            def start_suite(self, data: Any, result: Any) -> None:
                _start_suite(data, result)

            def end_suite(self, data: Any, result: Any) -> None:
                _end_suite(data, result)

    else:
        # RF < 7: keyword hooks get a single `args` object with `.data`/`.result`;
        # suite/test hooks get a single combined model — forward it as both.
        class _ForwardingLogger:  # type: ignore[no-redef]
            def start_keyword(self, args: Any) -> None:
                _start(args.data, args.result)

            def end_keyword(self, args: Any) -> None:
                _end(args.data, args.result)

            def start_test(self, model: Any) -> None:
                _start_test(model, model)

            def end_test(self, model: Any) -> None:
                _end_test(model, model)

            def start_suite(self, model: Any) -> None:
                _start_suite(model, model)

            def end_suite(self, model: Any) -> None:
                _end_suite(model, model)

    logger = _ForwardingLogger()
    LOGGER.register_logger(logger)
    try:
        with io.StringIO(suite_text) as src:
            model = get_model(src)
        model.source = _SOURCE
        suite = _RobotSuite.from_model(model)
        suite.run(output=None, log=None, report=None, console="none", stdout=io.StringIO(), stderr=io.StringIO())
    finally:
        LOGGER.unregister_logger(logger)


class _StackProbe:
    """Snapshots the controller's stack each time a target keyword starts."""

    def __init__(self, controller: DebugController, target_short_name: str) -> None:
        self.controller = controller
        self.target = target_short_name
        self.snapshots: List[List[Tuple[str, str, bool]]] = []

    def start_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        # The controller is registered first, so its stack already includes the
        # frame just pushed for this event.
        stack = self.controller.stack
        if stack and stack[-1].short_name == self.target:
            self.snapshots.append([(f.short_name, f.type, f.executed) for f in stack])

    def end_keyword(self, data: "running.Keyword", result: "result.Keyword") -> None:
        pass

    def start_test(self, data: Any, result: Any) -> None:
        pass

    def end_test(self, data: Any, result: Any) -> None:
        pass

    def start_suite(self, data: Any, result: Any) -> None:
        pass

    def end_suite(self, data: Any, result: Any) -> None:
        pass


def test_controller_tracks_keyword_call_stack() -> None:
    controller = DebugController()
    probe = _StackProbe(controller, "No Operation")
    _run_with_observers(SUITE, controller, probe)  # controller first -> notified first

    assert probe.snapshots, "probe never fired"
    # First executed `No Operation` is inside Inner Keyword <- Outer Keyword.
    names = [name for name, _type, _executed in probe.snapshots[0]]
    assert names[-3:] == ["Outer Keyword", "Inner Keyword", "No Operation"]
    # the frame is really executed
    assert probe.snapshots[0][-1][2] is True
    # stack is balanced once the run finishes
    assert controller.stack == []


def test_controller_marks_not_run_frames() -> None:
    controller = DebugController()
    probe = _StackProbe(controller, "Fail")
    _run_with_observers(SUITE, controller, probe)

    assert probe.snapshots, "the (not-taken) Fail keyword never produced a start event"
    fail_short, _type, executed = probe.snapshots[0][-1]
    assert fail_short == "Fail"
    assert executed is False  # untaken ELSE branch -> NOT RUN


# ---------------------------------------------------------------------------
# Phase 2b: breakpoints + stepping + the wait_at_stop pause.
# ---------------------------------------------------------------------------

# Line numbers matter for the breakpoint tests:
#   12 = `Log    before`, 13 = `Outer Keyword`, 7 = `Inner Keyword` call,
#   3 = `Log    inner-1`, 4 = `Log    inner-2`, 8 = `Log    outer-after`.
STEP_SUITE = """\
*** Keywords ***
Inner Keyword
    Log    inner-1
    Log    inner-2

Outer Keyword
    Inner Keyword
    Log    outer-after

*** Test Cases ***
T
    Log    before
    Outer Keyword
    Log    after
"""


class RecordingFrontend:
    """Scripted front-end: records every stop and replays a list of actions."""

    def __init__(
        self,
        script: Optional[List[ResumeAction]] = None,
        at_stop: Optional[Callable[[StopEvent], Optional[ResumeAction]]] = None,
    ) -> None:
        self.script: List[ResumeAction] = list(script or [])
        self.stops: List[Tuple[StopReason, str, Any]] = []
        self._at_stop = at_stop

    def wait_at_stop(self, stop: StopEvent) -> ResumeAction:
        self.stops.append((stop.reason, stop.frame.short_name, stop.frame.line))
        if self._at_stop is not None:
            action = self._at_stop(stop)
            if action is not None:
                return action
        return self.script.pop(0) if self.script else ResumeAction.CONTINUE

    def on_output(self, text: str, category: str = "console") -> None:
        pass

    def on_continued(self) -> None:
        pass

    def on_exited(self, exit_code: int) -> None:
        pass


def test_line_breakpoint_stops_at_that_line() -> None:
    frontend = RecordingFrontend()
    controller = DebugController(frontend)
    controller.set_line_breakpoints(_SOURCE, [12])  # `Log    before`
    _run_with_observers(STEP_SUITE, controller)

    assert frontend.stops == [(StopReason.BREAKPOINT, "Log", 12)]


def test_stack_includes_suite_and_test_frames() -> None:
    # The backtrace shows the full call chain: the suite and test sit below the
    # keyword frames (pushed at start_suite/start_test, popped at their ends).
    grabbed: List[List[Tuple[str, str]]] = []

    def _grab(stop: StopEvent) -> Optional[ResumeAction]:
        grabbed.append([(f.type, f.short_name) for f in stop.stack])
        return None

    controller = DebugController(RecordingFrontend(at_stop=_grab))
    controller.set_line_breakpoints(_SOURCE, [12])  # `Log    before`, directly in test T
    _run_with_observers(STEP_SUITE, controller)

    assert grabbed, "never stopped"
    stack = grabbed[0]
    assert stack[0][0] == "SUITE"  # bottom frame is the suite
    assert stack[1] == ("TEST", "T")  # then the test, by name
    assert stack[-1] == ("KEYWORD", "Log")  # innermost is the breakpoint keyword


def test_keyword_name_breakpoint_stops() -> None:
    frontend = RecordingFrontend()
    controller = DebugController(frontend)
    controller.set_keyword_breakpoints(["Inner Keyword"])
    _run_with_observers(STEP_SUITE, controller)

    assert [(reason, name) for reason, name, _line in frontend.stops] == [(StopReason.BREAKPOINT, "Inner Keyword")]


def test_stepping_in_over_out() -> None:
    frontend = RecordingFrontend(
        script=[
            ResumeAction.STEP_IN,  # Outer Keyword -> Inner Keyword
            ResumeAction.STEP_IN,  # Inner Keyword -> Log inner-1
            ResumeAction.STEP_OVER,  # Log inner-1 -> Log inner-2 (same level)
            ResumeAction.STEP_OUT,  # Log inner-2 -> Log outer-after (out of Inner Keyword)
            ResumeAction.CONTINUE,  # run to the end
        ]
    )
    controller = DebugController(frontend)
    controller.set_line_breakpoints(_SOURCE, [13])  # stop at the `Outer Keyword` call
    _run_with_observers(STEP_SUITE, controller)

    assert [(name, line) for _reason, name, line in frontend.stops] == [
        ("Outer Keyword", 13),
        ("Inner Keyword", 7),
        ("Log", 3),
        ("Log", 4),
        ("Log", 8),
    ]


def test_stop_on_entry_stops_once_at_first_keyword() -> None:
    frontend = RecordingFrontend()  # CONTINUE at the single entry stop
    controller = DebugController(frontend)
    controller.set_stop_on_entry(True)
    _run_with_observers(STEP_SUITE, controller)

    assert len(frontend.stops) == 1
    reason, name, line = frontend.stops[0]
    assert reason == StopReason.ENTRY
    assert (name, line) == ("Log", 12)  # first executed keyword: `Log    before`


# ---------------------------------------------------------------------------
# Phase 2c: per-frame scopes / variables + set_variable.
# ---------------------------------------------------------------------------

VAR_SUITE = """\
*** Variables ***
${SUITE_VAR}    suite-value

*** Keywords ***
Add Numbers
    [Arguments]    ${a}    ${b}
    ${sum}=    Evaluate    ${a} + ${b}
    Log    ${sum}

*** Test Cases ***
T
    Set Test Variable    ${TEST_VAR}    test-value
    ${result}=    Add Numbers    2    3
"""

# {scope_name: {var_name: value_repr}}
ScopeMap = Dict[str, Dict[str, str]]


def _scopes_of(controller: DebugController, frame: "StackFrame") -> ScopeMap:
    return {scope.name: {v.name: v.value for v in scope.variables} for scope in controller.get_scopes(frame)}


def _break_in_add_numbers(at_stop: Callable[[DebugController, "StackFrame"], Optional[ResumeAction]]) -> None:
    """Run `VAR_SUITE`, break on the inner `Log`, and hand the *enclosing*
    `Add Numbers` frame (where the locals live) to `at_stop`."""
    controller = DebugController()

    def _on_stop(stop: StopEvent) -> Optional[ResumeAction]:
        add_frame = stop.stack[-2]  # stack tail is `Add Numbers` <- `Log`
        assert add_frame.short_name == "Add Numbers"
        return at_stop(controller, add_frame)

    controller.set_frontend(RecordingFrontend(at_stop=_on_stop))
    controller.set_keyword_breakpoints(["Log"])
    _run_with_observers(VAR_SUITE, controller)


def test_get_scopes_separates_local_test_suite_global() -> None:
    captured: ScopeMap = {}

    def inspect(controller: DebugController, frame: "StackFrame") -> None:
        captured.update(_scopes_of(controller, frame))

    _break_in_add_numbers(inspect)

    assert {"Local", "Test", "Suite", "Global"} <= set(captured)
    # locals (args + assignment) surface only in Local, not the broader scopes
    assert {"${a}", "${b}", "${sum}"} <= set(captured["Local"])
    assert "${SUITE_VAR}" not in captured["Local"]
    # each value lands in the innermost scope that introduces it
    assert captured["Suite"].get("${SUITE_VAR}") == "'suite-value'"
    assert "${TEST_VAR}" in captured["Test"]
    assert "${SUITE_VAR}" not in captured["Global"]
    assert "${OUTPUT_DIR}" in captured["Global"]  # a built-in global


def test_set_variable_changes_the_value_in_scope() -> None:
    result: Dict[str, Any] = {}

    def mutate(controller: DebugController, frame: "StackFrame") -> None:
        result["returned"] = controller.set_variable(frame, "${sum}", "99")
        result["after"] = _scopes_of(controller, frame)
        with pytest.raises(NameError):
            controller.set_variable(frame, "${nope}", "1")

    _break_in_add_numbers(mutate)

    assert result["returned"] == "99"
    assert result["after"]["Local"]["${sum}"] == "99"


# ---------------------------------------------------------------------------
# Phase 2d: exception breakpoints (FAIL at end_keyword, before the unwind).
# ---------------------------------------------------------------------------

# Uncaught failure nested one keyword deep — the FAIL is re-reported at `Outer
# Keyword`'s end as it unwinds, so de-dup must stop only once (at `Fail`).
FAIL_SUITE = """\
*** Keywords ***
Outer Keyword
    Fail    boom

*** Test Cases ***
T
    Outer Keyword
"""

# Failure caught by TRY/EXCEPT — `Fail` and the TRY branch end FAIL, but the run
# does not abort, so an uncaught-only filter must NOT stop.
CAUGHT_TRY_SUITE = """\
*** Keywords ***
Wrapper
    TRY
        Fail    boom
    EXCEPT    boom
        Log    handled
    END

*** Test Cases ***
T
    Wrapper
"""

# First failure caught by the TRY; the EXCEPT handler itself fails — that second
# failure is uncaught and must re-arm + stop.
EXCEPT_BODY_FAIL_SUITE = """\
*** Keywords ***
Wrapper
    TRY
        Fail    first
    EXCEPT    first
        Fail    second
    END

*** Test Cases ***
T
    Wrapper
"""

# Failure swallowed by a `Run Keyword And …` catcher keyword.
CAUGHT_RKAEE_SUITE = """\
*** Test Cases ***
T
    Run Keyword And Expect Error    boom    Fail    boom
"""

# Uncaught failure in a keyword that also has a (passing) teardown. The teardown
# runs *during* the unwind; it must NOT clear the de-dup fence, or the same
# exception would stop again at `Has Teardown` as it propagates out.
TEARDOWN_AFTER_FAIL_SUITE = """\
*** Keywords ***
Has Teardown
    Fail    boom
    [Teardown]    Log    cleanup

*** Test Cases ***
T
    Has Teardown
"""

# A failing teardown is a genuinely new, uncaught failure — it must stop.
FAILING_TEARDOWN_SUITE = """\
*** Keywords ***
Has Teardown
    Log    ok
    [Teardown]    Fail    teardown boom

*** Test Cases ***
T
    Has Teardown
"""


def _run_with_exception_filters(
    suite_text: str,
    filters: List[str],
    script: Optional[List[ResumeAction]] = None,
    at_stop: Optional[Callable[[StopEvent], Optional[ResumeAction]]] = None,
) -> RecordingFrontend:
    frontend = RecordingFrontend(script=script, at_stop=at_stop)
    controller = DebugController(frontend)
    controller.set_exception_breakpoints(filters)
    _run_with_observers(suite_text, controller)
    return frontend


def _exception_stops(frontend: RecordingFrontend) -> List[Tuple[str, Any]]:
    return [(name, line) for reason, name, line in frontend.stops if reason == StopReason.EXCEPTION]


def test_uncaught_failure_stops_once_at_innermost_keyword() -> None:
    frontend = _run_with_exception_filters(FAIL_SUITE, ["uncaught_failed_keyword"])
    # exactly one stop, at `Fail` — NOT a second one at `Outer Keyword` as the
    # same exception unwinds through it.
    assert [name for name, _line in _exception_stops(frontend)] == ["Fail"]


def test_passing_teardown_does_not_cause_duplicate_exception_stop() -> None:
    # The keyword's teardown runs while the failure unwinds; it must not clear
    # the de-dup fence, so the same exception stops only once (at `Fail`), not
    # again at `Has Teardown`.
    frontend = _run_with_exception_filters(TEARDOWN_AFTER_FAIL_SUITE, ["uncaught_failed_keyword"])
    assert [name for name, _line in _exception_stops(frontend)] == ["Fail"]


def test_failing_teardown_still_stops() -> None:
    # A failure *in* the teardown is a new uncaught failure and must still stop.
    frontend = _run_with_exception_filters(FAILING_TEARDOWN_SUITE, ["uncaught_failed_keyword"])
    assert [name for name, _line in _exception_stops(frontend)] == ["Fail"]


def test_exception_breakpoints_disabled_by_default() -> None:
    # No set_exception_breakpoints call ⇒ empty filter set ⇒ a bare REPL run
    # never pauses on the user's own failures.
    frontend = RecordingFrontend()
    controller = DebugController(frontend)
    _run_with_observers(FAIL_SUITE, controller)
    assert _exception_stops(frontend) == []


def test_caught_by_try_except_does_not_stop_when_uncaught_only() -> None:
    frontend = _run_with_exception_filters(CAUGHT_TRY_SUITE, ["uncaught_failed_keyword"])
    assert _exception_stops(frontend) == []


def test_failed_keyword_filter_stops_even_when_caught() -> None:
    frontend = _run_with_exception_filters(CAUGHT_TRY_SUITE, ["failed_keyword"])
    assert [name for name, _line in _exception_stops(frontend)] == ["Fail"]


def test_except_body_failure_re_arms_and_stops() -> None:
    frontend = _run_with_exception_filters(EXCEPT_BODY_FAIL_SUITE, ["uncaught_failed_keyword"])
    # the caught `Fail first` is silent; the uncaught `Fail second` in the
    # handler stops exactly once.
    assert [name for name, _line in _exception_stops(frontend)] == ["Fail"]


def test_caught_by_run_keyword_and_expect_error_does_not_stop() -> None:
    frontend = _run_with_exception_filters(CAUGHT_RKAEE_SUITE, ["uncaught_failed_keyword"])
    assert _exception_stops(frontend) == []


def test_not_run_branch_failure_never_stops() -> None:
    # SUITE's untaken ELSE branch contains `Fail not taken` (status NOT RUN).
    frontend = _run_with_exception_filters(SUITE, ["failed_keyword"])
    assert _exception_stops(frontend) == []


def test_continue_at_exception_stop_lets_failure_propagate() -> None:
    frontend = RecordingFrontend(script=[ResumeAction.CONTINUE])
    controller = DebugController(frontend)
    controller.set_exception_breakpoints(["uncaught_failed_keyword"])
    _run_with_observers(FAIL_SUITE, controller)
    # the controller did not swallow the failure — the stack unwound cleanly.
    assert len(_exception_stops(frontend)) == 1
    assert controller.stack == []


class _FailEvent:
    """A synthetic failing-keyword event (serves as both `data` and `result`)."""

    type = "KEYWORD"
    name = "Fail"
    full_name = "BuiltIn.Fail"
    status = "FAIL"
    source = None
    lineno = None
    message = "boom"


def test_terminate_action_raises_debug_terminated() -> None:
    # Driven directly with synthetic events: Robot's suite.run() swallows any
    # BaseException raised from a logger callback (verified RF 5/6/7), so the
    # TERMINATE -> DebugTerminated contract is a controller-level signal — the
    # run-driver turns it into an actual abort (Phase 3), it does not unwind
    # through suite.run() on its own.
    controller = DebugController(RecordingFrontend(script=[ResumeAction.TERMINATE]))
    controller.set_exception_breakpoints(["failed_keyword"])
    event: Any = _FailEvent()
    controller.start_keyword(event, event)
    with pytest.raises(DebugTerminated):
        controller.end_keyword(event, event)


def test_suppressed_run_does_not_stop_on_exception() -> None:
    frontend = RecordingFrontend()
    controller = DebugController(frontend)
    controller.set_exception_breakpoints(["failed_keyword"])
    with controller.suppress_pausing():
        _run_with_observers(FAIL_SUITE, controller)
    assert _exception_stops(frontend) == []


def test_exception_stop_description_carries_message_on_rf7() -> None:
    descriptions: List[str] = []

    def capture(stop: StopEvent) -> Optional[ResumeAction]:
        descriptions.append(stop.description)
        return None

    frontend = RecordingFrontend(at_stop=capture)
    controller = DebugController(frontend)
    controller.set_exception_breakpoints(["uncaught_failed_keyword"])
    _run_with_observers(FAIL_SUITE, controller)

    assert len(descriptions) == 1
    if RF_VERSION >= (7, 0):
        assert "boom" in descriptions[0]  # RF7 populates result.message at the end hook
    else:
        assert descriptions[0] == "Keyword failed."  # RF5/6 leave it empty


# A suite that fully passes — no test/suite end should ever fire an exception stop.
PASS_SUITE = """\
*** Test Cases ***
T
    Log    ok
"""


def _typed_stops(at: List[Tuple[StopReason, str, str]]) -> Callable[[StopEvent], Optional[ResumeAction]]:
    """An `at_stop` callback that records (reason, frame.type, frame.short_name)."""

    def _record(stop: StopEvent) -> Optional[ResumeAction]:
        at.append((stop.reason, stop.frame.type, stop.frame.short_name))
        return None

    return _record


def test_failed_test_filter_stops_at_test_end() -> None:
    stops: List[Tuple[StopReason, str, str]] = []
    _run_with_exception_filters(FAIL_SUITE, ["failed_test"], at_stop=_typed_stops(stops))
    assert stops == [(StopReason.EXCEPTION, "TEST", "T")]


def test_failed_suite_filter_stops_at_suite_end() -> None:
    stops: List[Tuple[StopReason, str, str]] = []
    _run_with_exception_filters(FAIL_SUITE, ["failed_suite"], at_stop=_typed_stops(stops))
    assert len(stops) == 1
    assert (stops[0][0], stops[0][1]) == (StopReason.EXCEPTION, "SUITE")


def test_failed_test_filter_does_not_stop_when_all_pass() -> None:
    stops: List[Tuple[StopReason, str, str]] = []
    _run_with_exception_filters(PASS_SUITE, ["failed_test", "failed_suite"], at_stop=_typed_stops(stops))
    assert stops == []


def test_failed_keyword_and_failed_test_stop_independently() -> None:
    # both filters armed: the uncaught keyword failure stops at the keyword, then
    # the test end stops again — two distinct exception stops.
    stops: List[Tuple[StopReason, str, str]] = []
    _run_with_exception_filters(FAIL_SUITE, ["uncaught_failed_keyword", "failed_test"], at_stop=_typed_stops(stops))
    assert [(t, n) for _reason, t, n in stops] == [("KEYWORD", "Fail"), ("TEST", "T")]


# ---------------------------------------------------------------------------
# Review follow-ups: subscripted inspection, on-demand pause, control-structure
# stepping.
# ---------------------------------------------------------------------------

SUBSCRIPT_SUITE = """\
*** Keywords ***
Make
    ${items}=    Evaluate    [10, 20, 30]
    Log    ${items}

*** Test Cases ***
T
    Make
"""


def test_evaluate_expression_handles_subscripted_variable() -> None:
    captured: Dict[str, Any] = {}
    controller = DebugController()

    def at_stop(stop: StopEvent) -> Optional[ResumeAction]:
        frame = stop.stack[-2]  # `Make` (parent of the inner `Log`)
        captured["whole"] = controller.evaluate_expression(frame, "${items}")
        captured["item"] = controller.evaluate_expression(frame, "${items}[1]")
        return None

    controller.set_frontend(RecordingFrontend(at_stop=at_stop))
    controller.set_keyword_breakpoints(["Log"])
    _run_with_observers(SUBSCRIPT_SUITE, controller)

    assert captured["whole"] == [10, 20, 30]
    assert captured["item"] == 20  # item access, type preserved (int)


def test_request_pause_stops_at_next_executed_keyword() -> None:
    frontend = RecordingFrontend()
    controller = DebugController(frontend)
    controller.request_pause()
    _run_with_observers(STEP_SUITE, controller)

    assert len(frontend.stops) == 1
    reason, _name, _line = frontend.stops[0]
    assert reason == StopReason.PAUSE


def test_stepping_descends_through_for_and_if() -> None:
    # Stop at the FOR, then keep stepping in — execution descends
    # FOR -> ITERATION -> IF -> the `No Operation` in the taken branch.
    frontend = RecordingFrontend(script=[ResumeAction.STEP_IN] * 6 + [ResumeAction.CONTINUE])
    controller = DebugController(frontend)
    controller.set_line_breakpoints(_SOURCE, [11])  # the `FOR` line
    _run_with_observers(SUITE, controller)

    names = [name for _reason, name, _line in frontend.stops]
    assert "No Operation" in names  # reached the taken IF branch by stepping in
    assert "Fail" not in names  # the untaken ELSE branch is never stepped into


# ---------------------------------------------------------------------------
# Phase 5: .until (UNTIL stepping), breakpoint-record attributes
# (condition / ignore-count / logpoint), set_*_breakpoints replace semantics.
# ---------------------------------------------------------------------------

# Log start = 3, FOR = 4, Log ${i} = 5, END = 6, Log done = 7
UNTIL_LOOP_SUITE = """\
*** Test Cases ***
T
    Log    start
    FOR    ${i}    IN RANGE    3
        Log    ${i}
    END
    Log    done
"""


def _until_loop_stops(action_at_iteration: ResumeAction) -> List[Tuple[StopReason, str, Any]]:
    """Run UNTIL_LOOP_SUITE; STEP_IN from `Log start` down to the first loop
    iteration frame, issue `action_at_iteration` there, then CONTINUE. Returns
    every recorded stop. The descent keys off `type == "FOR"` (the FOR *root*,
    same type on every RF version) so it is version-robust."""
    stops: List[Tuple[StopReason, str, Any]] = []
    state = {"phase": "find_for"}

    def at_stop(stop: StopEvent) -> Optional[ResumeAction]:
        f = stop.frame
        stops.append((stop.reason, f.short_name, f.line))
        if state["phase"] == "done":
            return ResumeAction.CONTINUE
        if state["phase"] == "find_for":
            if f.type == "FOR":  # the FOR root — step once more to land in the iteration
                state["phase"] = "at_iteration"
            return ResumeAction.STEP_IN
        state["phase"] = "done"  # this stop is the loop iteration
        return action_at_iteration

    controller = DebugController(RecordingFrontend(at_stop=at_stop))
    controller.set_line_breakpoints(_SOURCE, [3])  # `Log start`, fires once
    _run_with_observers(UNTIL_LOOP_SUITE, controller)
    return stops


def test_until_skips_remaining_loop_iterations() -> None:
    # UNTIL's defining behavior: issued at a loop iteration, it runs PAST the
    # remaining iterations (same line) and stops at the next later line in the
    # enclosing frame — `Log done` (line 7) — never on the inner loop body.
    stops = _until_loop_stops(ResumeAction.UNTIL)
    assert (StopReason.STEP, "Log", 7) in stops
    assert all(line != 5 for _r, _n, line in stops)  # the inner loop body was skipped


def test_next_stops_at_next_iteration_where_until_would_skip() -> None:
    # The contrast that pins UNTIL != STEP_OVER: STEP_OVER at the same iteration
    # stops AGAIN at the next iteration (the FOR line 4); it does not reach the
    # post-loop `Log done` (line 7).
    stops = _until_loop_stops(ResumeAction.STEP_OVER)
    assert (StopReason.STEP, "Log", 7) not in stops
    iteration_step_stops = [line for reason, _n, line in stops if reason == StopReason.STEP and line == 4]
    assert len(iteration_step_stops) >= 2  # FOR root + at least one iteration re-stop


# Log only = 3 (inside Wrapper), Wrapper call = 7, Log after = 8
UNTIL_RETURN_SUITE = """\
*** Keywords ***
Wrapper
    Log    only

*** Test Cases ***
T
    Wrapper
    Log    after
"""


def test_until_returns_to_caller_when_no_later_line() -> None:
    # Issued on the last line of a keyword body (no later line to reach), UNTIL
    # takes the shallower-stack branch and stops in the caller at the next
    # sibling (`Log after`, line 8).
    stops: List[Tuple[StopReason, str, Any]] = []

    def at_stop(stop: StopEvent) -> Optional[ResumeAction]:
        stops.append((stop.reason, stop.frame.short_name, stop.frame.line))
        if stop.frame.line == 3:  # `Log only`
            return ResumeAction.UNTIL
        return ResumeAction.CONTINUE

    controller = DebugController(RecordingFrontend(at_stop=at_stop))
    controller.set_line_breakpoints(_SOURCE, [3])  # `Log only`, fires once
    _run_with_observers(UNTIL_RETURN_SUITE, controller)

    assert (StopReason.STEP, "Log", 8) in stops


def test_set_line_breakpoints_replaces_prior_set_and_keeps_other_kind() -> None:
    # A second set_line_breakpoints call replaces the prior line set; a keyword
    # breakpoint (a different kind) is untouched. No run needed.
    controller = DebugController()
    controller.set_keyword_breakpoints(["Login"])
    controller.set_line_breakpoints(_SOURCE, [10])
    controller.set_line_breakpoints(_SOURCE, [20])  # replaces line 10

    line_bps = [bp.line for bp in controller.breakpoints if bp.kind == "line"]
    kw_bps = [bp.name for bp in controller.breakpoints if bp.kind == "keyword"]
    assert line_bps == [20]
    assert kw_bps == ["Login"]


# FOR over RANGE 3 with a single `Log ${i}` body — for logpoint + condition tests.
LOOP3_SUITE = """\
*** Test Cases ***
T
    FOR    ${i}    IN RANGE    3
        Log    ${i}
    END
"""


class _OutputRecordingFrontend(RecordingFrontend):
    """RecordingFrontend that also captures `on_output` text."""

    def __init__(self) -> None:
        super().__init__()
        self.outputs: List[str] = []

    def on_output(self, text: str, category: str = "console") -> None:
        self.outputs.append(text)


def test_logpoint_substitutes_variables_and_never_stops() -> None:
    frontend = _OutputRecordingFrontend()
    controller = DebugController(frontend)
    controller.add_keyword_breakpoint("Log", log_message="i is ${i}")
    _run_with_observers(LOOP3_SUITE, controller)

    assert frontend.stops == []  # a logpoint logs + continues, it never pauses
    assert "i is 0" in frontend.outputs  # ${i} resolved against the runtime store
    assert "i is 1" in frontend.outputs
    assert "i is 2" in frontend.outputs


def test_false_condition_does_not_consume_ignore_count() -> None:
    # Ordering proof: a non-truthy condition returns BEFORE the hit counter is
    # bumped, so false hits don't eat an ignore slot.
    frontend = RecordingFrontend()
    controller = DebugController(frontend)
    bp = controller.add_keyword_breakpoint("Log", condition="${i} == 1")
    bp.ignore_count = 1
    _run_with_observers(LOOP3_SUITE, controller)

    # i=0 false (no hit), i=1 true (hit=1, ignored as 1<=1), i=2 false (no hit)
    # => never stops. If the condition were evaluated AFTER counting, i=0/i=2
    #    would consume the ignore slot and i==1 would stop.
    assert frontend.stops == []
