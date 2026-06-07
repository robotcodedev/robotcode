"""Tests for the CLI debugger — the `ConsoleInterpreter` *is* the debug front-end.

Integration tests drive a real in-process suite through the *interpreter's own*
logger (enabled via `forward_events`), with the `DebugController` registered as
an observer and the interpreter's `read_line` swapped for a scripted reader —
the same wiring `repl robot` uses, minus the runner. Output is captured through
a stub `Application`. Pure command-resolution tests need no run.
"""

import io
import tempfile
from pathlib import Path
from typing import IO, Any, AnyStr, Callable, List, Optional, Tuple, Union, cast

import pytest
from robot.api import TestSuite as _RobotSuite
from robot.api import get_model
from robot.output import LOGGER

from robotcode.plugin import Application
from robotcode.repl._debug.controller import DebugController
from robotcode.repl._debug.types import ResumeAction, StackFrame, StopEvent, StopReason
from robotcode.repl.console_interpreter import ConsoleInterpreter
from robotcode.robot.utils import RF_VERSION

# A writable temp path (not a hardcoded "/tmp/…", which is not writable on Windows).
_SOURCE = str(Path(tempfile.gettempdir()) / "dbg_console_suite.robot")

#  11 = `Log    before`, 12 = `Outer`
STEP_SUITE = """\
*** Keywords ***
Inner
    Log    inner

Outer
    Inner
    Log    outer

*** Test Cases ***
T
    Log    before
    Outer
"""

VAR_SUITE = """\
*** Variables ***
${SUITE_VAR}    sv

*** Keywords ***
Add
    [Arguments]    ${a}    ${b}
    ${sum}=    Evaluate    ${a} + ${b}
    Log    ${sum}

*** Test Cases ***
T
    ${r}=    Add    2    3
"""

BREAKPOINT_SUITE = """\
*** Settings ***
Library    robotcode.repl.Repl

*** Test Cases ***
T
    Log    before
    Breakpoint
    Log    after
"""


class _CaptureApp(Application):
    """Real `Application` whose echo channel captures into a list."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: List[str] = []

    def echo(
        self,
        message: Union[str, Callable[[], Any], None],
        file: Optional[IO[AnyStr]] = None,
        nl: bool = True,
        err: bool = False,
    ) -> None:
        self.messages.append(message() if callable(message) else str(message))


class _Reader:
    """Scripted line reader — pops queued lines, then signals EOF.

    Installed as the interpreter's `read_line`, so it accepts (and ignores)
    the `completer`/`prefill`/… keyword arguments the real one takes.
    """

    def __init__(self, lines: List[str]) -> None:
        self._lines = list(lines)

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        if not self._lines:
            raise EOFError
        return self._lines.pop(0)


def _run_debug(
    suite_text: str,
    reader_lines: List[str],
    *,
    stop_on_entry: bool = False,
    line_breakpoints: Optional[List[int]] = None,
    keyword_breakpoints: Optional[List[str]] = None,
    exception_filters: Optional[List[str]] = None,
    prepare: Optional[Callable[[ConsoleInterpreter], None]] = None,
) -> List[str]:
    """Run `suite_text` with the console debugger attached; return echoed lines.

    `prepare`, if given, is called with the interpreter before the run — used to
    capture `show_doc` or otherwise tweak the front-end.
    """
    app = _CaptureApp()
    interpreter = ConsoleInterpreter(app=app)
    interpreter.source = Path(_SOURCE)
    controller = DebugController()
    controller.set_frontend(interpreter)
    interpreter.set_controller(controller)
    interpreter.register_observer(controller)
    # Swap the prompt reader for a scripted one (the interpreter *is* the
    # front-end, so its own `read_line` drives the debug prompt).
    interpreter.read_line = _Reader(reader_lines)  # type: ignore[method-assign]
    if prepare is not None:
        prepare(interpreter)

    if stop_on_entry:
        controller.set_stop_on_entry(True)
    if line_breakpoints:
        controller.set_line_breakpoints(_SOURCE, line_breakpoints)
    if keyword_breakpoints:
        controller.set_keyword_breakpoints(keyword_breakpoints)
    if exception_filters:
        controller.set_exception_breakpoints(exception_filters)

    try:
        with interpreter.forward_events(echo_messages=False):
            with io.StringIO(suite_text) as src:
                model = get_model(src)
            model.source = _SOURCE
            suite = _RobotSuite.from_model(model)
            suite.run(output=None, log=None, report=None, console="none", stdout=io.StringIO(), stderr=io.StringIO())
    finally:
        interpreter.unregister_observer(controller)
        LOGGER.unregister_logger(interpreter._logger)

    return app.messages


def _stop_lines(messages: List[str]) -> List[str]:
    return [m for m in messages if m.startswith("* ")]


# ---------------------------------------------------------------------------
# Integration — stop rendering, navigation, inspection, evaluation
# ---------------------------------------------------------------------------


def test_stop_on_entry_renders_then_continues() -> None:
    messages = _run_debug(STEP_SUITE, [".continue"], stop_on_entry=True)
    stops = _stop_lines(messages)
    assert len(stops) == 1
    assert stops[0].startswith("* entry")
    assert "Log" in stops[0]


def test_where_renders_innermost_first() -> None:
    messages = _run_debug(STEP_SUITE, [".where", ".continue"], keyword_breakpoints=["Inner"])
    text = "\n".join(messages)
    assert "#0  Inner" in text
    assert "#1  Outer" in text


def test_up_then_vars_shows_enclosing_keyword_locals() -> None:
    # Stop at the inner `Log`; its own frame has no locals, so move up to the
    # `Add` frame, whose scope carries the arguments + assignment.
    messages = _run_debug(VAR_SUITE, [".up", ".vars", ".continue"], keyword_breakpoints=["Log"])
    text = "\n".join(messages)
    assert "Local:" in text
    assert "${a} = '2'" in text  # args arrive as strings
    assert "${sum} = 5" in text  # Evaluate `2 + 3` → int
    # the suite variable lands in its own scope, not Local
    assert "Suite:" in text
    assert "${SUITE_VAR} = 'sv'" in text


def test_evaluate_runs_keyword_in_paused_context() -> None:
    messages = _run_debug(STEP_SUITE, ["Set Variable    42", ".continue"], stop_on_entry=True)
    assert "=> '42'" in messages


def test_evaluated_variable_is_visible_afterwards() -> None:
    messages = _run_debug(
        VAR_SUITE,
        [".up", "Set Test Variable    ${injected}    hi", ".vars", ".continue"],
        keyword_breakpoints=["Log"],
    )
    text = "\n".join(messages)
    assert "${injected} = 'hi'" in text


def test_step_over_advances_to_next_keyword() -> None:
    messages = _run_debug(STEP_SUITE, [".next", ".continue"], stop_on_entry=True)
    stops = _stop_lines(messages)
    assert len(stops) == 2
    assert stops[0].startswith("* entry")
    assert "Log" in stops[0]
    assert stops[1].startswith("* step")
    assert "Outer" in stops[1]


def test_eof_at_prompt_continues() -> None:
    # An empty script → reader raises EOFError immediately → treated as continue.
    messages = _run_debug(STEP_SUITE, [], stop_on_entry=True)
    assert len(_stop_lines(messages)) == 1  # stopped once, then ran to the end


# ---------------------------------------------------------------------------
# 3b — embedded Breakpoint keyword, .print/.set, runtime breakpoint management
# ---------------------------------------------------------------------------


def test_embedded_breakpoint_keyword_stops() -> None:
    # No triggers configured — the `Breakpoint` keyword alone pauses the run.
    messages = _run_debug(BREAKPOINT_SUITE, [".continue"])
    stops = _stop_lines(messages)
    assert len(stops) == 1
    assert stops[0].startswith("* breakpoint")
    assert "Breakpoint" in stops[0]


def test_print_evaluates_variable_and_expression() -> None:
    messages = _run_debug(
        VAR_SUITE, [".up", ".print ${a}", ".print ${a} + ${b}", ".continue"], keyword_breakpoints=["Log"]
    )
    text = "\n".join(messages)
    assert "${a} = '2'" in text  # bare reference → raw value (string)
    assert "${a} + ${b} = 5" in text  # expression → evaluated (int)


def test_set_changes_variable() -> None:
    messages = _run_debug(
        VAR_SUITE, [".up", ".set ${a} world", ".print ${a}", ".continue"], keyword_breakpoints=["Log"]
    )
    # .set stores the literal (substituted) string — like `Set Variable`
    assert "${a} = 'world'" in messages


def test_break_added_at_runtime_triggers() -> None:
    messages = _run_debug(STEP_SUITE, [".break Outer", ".continue", ".continue"], stop_on_entry=True)
    stops = _stop_lines(messages)
    assert len(stops) == 2
    assert stops[0].startswith("* entry")
    assert stops[1].startswith("* breakpoint")
    assert "Outer" in stops[1]


def test_breakpoints_lists_active() -> None:
    messages = _run_debug(STEP_SUITE, [".break Nonexistent", ".breakpoints", ".continue"], stop_on_entry=True)
    text = "\n".join(messages)
    assert "#1  keyword Nonexistent" in text  # numbered listing


def test_catch_sets_and_shows_exception_filter() -> None:
    messages = _run_debug(STEP_SUITE, [".catch uncaught", ".catch", ".continue"], stop_on_entry=True)
    # Both `.catch uncaught` (set) and bare `.catch` (show) echo a `catching:`
    # line with the armed filter — so exactly two such lines appear.
    catching = [m for m in messages if m.startswith("catching:") and "uncaught_failed_keyword" in m]
    assert len(catching) == 2


# ---------------------------------------------------------------------------
# 3c — detach (let the run finish) and quit (abort)
# ---------------------------------------------------------------------------


def test_detach_disables_further_stops() -> None:
    # Stop at entry, detach → the later `Outer` keyword breakpoint never fires.
    messages = _run_debug(STEP_SUITE, [".detach"], stop_on_entry=True, keyword_breakpoints=["Outer"])
    assert len(_stop_lines(messages)) == 1


def test_abort_aborts_the_run() -> None:
    # `.abort` exits via SystemExit (the only thing Robot propagates from a
    # logger callback); the run does not finish.
    with pytest.raises(SystemExit):
        _run_debug(STEP_SUITE, [".abort"], stop_on_entry=True)


# ---------------------------------------------------------------------------
# Command resolution (pure — no run needed)
# ---------------------------------------------------------------------------


def _bare_interpreter() -> ConsoleInterpreter:
    # Only command-resolution is exercised; no run, no app needed. Unregister the
    # logger the interpreter registers on construction so these run-less tests
    # don't leak a global LOGGER logger that would fire during later tests.
    interp = ConsoleInterpreter(app=None)
    LOGGER.unregister_logger(interp._logger)
    return interp


def test_alias_and_prefix_resolution() -> None:
    interp = _bare_interpreter()
    assert interp._resolve_dot_command("c") == ("_continue", None)  # short alias wins
    assert interp._resolve_dot_command("continue") == ("_continue", None)  # exact long
    assert interp._resolve_dot_command("cont")[0] == "_continue"  # unambiguous prefix
    assert interp._resolve_dot_command("s") == ("_step", None)  # short alias
    assert interp._resolve_dot_command("frame")[0] == "_frame"
    assert interp._resolve_dot_command("p") == ("_print", None)
    assert interp._resolve_dot_command("b") == ("_break", None)
    assert interp._resolve_dot_command("bp") == ("_breakpoints", None)
    assert interp._resolve_dot_command("abort") == ("_abort", None)
    # Session commands resolve through the same table.
    assert interp._resolve_dot_command("kw") == ("_kw", None)


def test_ambiguous_prefix_reports_matches() -> None:
    interp = _bare_interpreter()
    attr, error = interp._resolve_dot_command("br")  # break / breakpoints
    assert attr is None
    assert error is not None
    assert ".break" in error
    assert ".breakpoints" in error


def test_cross_group_prefix_is_ambiguous() -> None:
    # Resolving over the unified table means a prefix can now straddle the
    # Session and Debugger groups: `.do` matches `.doc` (session) and `.down`
    # (debugger), so it must report ambiguity rather than guess.
    interp = _bare_interpreter()
    attr, error = interp._resolve_dot_command("do")
    assert attr is None
    assert error is not None
    assert ".doc" in error
    assert ".down" in error


def test_unknown_command_reports_error() -> None:
    interp = _bare_interpreter()
    attr, error = interp._resolve_dot_command("nope")
    assert attr is None
    assert error is not None
    assert "Unknown" in error


def _fake_stop() -> StopEvent:
    frame = StackFrame(name="Log", type="KEYWORD", source=_SOURCE, line=1, depth=0)
    return StopEvent(reason=StopReason.ENTRY, frame=frame, stack=[frame])


def test_wait_at_stop_reads_through_interpreter_read_line() -> None:
    # The interpreter *is* the front-end: `wait_at_stop` reads via its own
    # `read_line`, threading the debug completer built in `set_controller`.
    app = _CaptureApp()
    interpreter = ConsoleInterpreter(app=app)
    controller = DebugController()
    controller.set_frontend(interpreter)
    interpreter.set_controller(controller)

    seen: List[Tuple[str, Any]] = []

    def _record(prompt: str, *, completer: Any = None, **kwargs: Any) -> str:
        seen.append((prompt, completer))
        return ".continue"

    interpreter.read_line = _record  # type: ignore[method-assign]
    try:
        action = interpreter.wait_at_stop(_fake_stop())
    finally:
        LOGGER.unregister_logger(interpreter._logger)

    assert action is ResumeAction.CONTINUE
    assert seen == [("(rdb) ", interpreter._debug_completer)]
    assert interpreter._stop is None  # stop state cleared on resume
    assert interpreter._pending_action is None


def test_wait_at_stop_clears_state_when_abort_unwinds() -> None:
    # `.abort` raises SystemExit straight through the prompt loop; the stop state
    # must STILL be cleared (try/finally) so the interactive shell prompt isn't
    # left wedged in a phantom debug state after the run unwinds.
    app = _CaptureApp()
    interpreter = ConsoleInterpreter(app=app)
    controller = DebugController()
    controller.set_frontend(interpreter)
    interpreter.set_controller(controller)
    interpreter.read_line = _Reader([".abort"])  # type: ignore[method-assign]
    try:
        with pytest.raises(SystemExit):
            interpreter.wait_at_stop(_fake_stop())
    finally:
        LOGGER.unregister_logger(interpreter._logger)
    assert interpreter._stop is None
    assert interpreter._pending_action is None


def test_help_lists_session_and_debugger_commands() -> None:
    app = _CaptureApp()
    interpreter = ConsoleInterpreter(app=app)
    shown: List[Tuple[str, str]] = []
    interpreter.show_doc = lambda title, markdown, *, scroll_to=None: shown.append((title, markdown))  # type: ignore[method-assign]
    try:
        interpreter._dispatch_dot_command(".help")
    finally:
        LOGGER.unregister_logger(interpreter._logger)
    assert len(shown) == 1
    title, body = shown[0]
    assert title == "Dot-commands"
    assert "### Session" in body
    assert "### Debugger" in body
    assert body.index("### Session") < body.index("### Debugger")  # group order
    assert ".continue" in body  # a debugger command
    assert ".kw" in body  # session command
    assert ".vars" in body  # session command


# ---------------------------------------------------------------------------
# Review follow-ups: subscripted .print, frame navigation, .break path:line,
# .catch multi/off.
# ---------------------------------------------------------------------------

LIST_SUITE = """\
*** Keywords ***
Make
    ${items}=    Evaluate    [10, 20, 30]
    Log    done

*** Test Cases ***
T
    Make
"""


def test_print_subscripted_variable() -> None:
    messages = _run_debug(
        LIST_SUITE, [".up", ".print ${items}", ".print ${items}[1]", ".continue"], keyword_breakpoints=["Log"]
    )
    text = "\n".join(messages)
    assert "${items} = [10, 20, 30]" in text
    assert "${items}[1] = 20" in text  # item access, type preserved


def test_frame_up_down_and_select_by_number() -> None:
    messages = _run_debug(VAR_SUITE, [".up", ".down", ".frame 1", ".continue"], keyword_breakpoints=["Log"])
    text = "\n".join(messages)
    assert "#1  Add" in text  # .up / .frame 1 select the enclosing keyword (suite-local, no prefix)
    assert "#0  BuiltIn.Log" in text  # .down returns to the innermost frame, shown with its full name


def test_frame_invalid_number_shows_usage() -> None:
    messages = _run_debug(VAR_SUITE, [".frame nope", ".continue"], keyword_breakpoints=["Log"])
    assert any("usage: .frame" in m for m in messages)


def test_break_with_path_line_format_triggers() -> None:
    messages = _run_debug(STEP_SUITE, [f".break {_SOURCE}:12", ".continue", ".continue"], stop_on_entry=True)
    stops = _stop_lines(messages)
    assert len(stops) == 2
    assert stops[0].startswith("* entry")
    # The location is shown relative to the cwd (a `…/`-prefixed path here, since
    # the test source lives in a temp dir); assert the filename:line suffix, which
    # is stable regardless of where the tests run from.
    assert "dbg_console_suite.robot:12)" in stops[1]  # the line breakpoint fired


def test_catch_multiple_filters_then_off() -> None:
    messages = _run_debug(STEP_SUITE, [".catch uncaught test", ".catch off", ".catch", ".continue"], stop_on_entry=True)
    text = "\n".join(messages)
    assert "failed_test" in text  # both set at once
    assert "uncaught_failed_keyword" in text
    # `.catch off` and the bare `.catch` after it both report the empty set
    assert text.count("catching: (none)") == 2


# ---------------------------------------------------------------------------
# Unified prompt: session commands work at a stop (incl. the doc viewer), and
# debugger navigation commands report when there's nothing to act on.
# ---------------------------------------------------------------------------


def test_session_command_opens_doc_viewer_at_stop() -> None:
    # `.kw` (a session command) works at a debug stop and routes through the
    # same `show_doc` path the shell prompt uses — so `repl robot` gets the
    # doc viewer at a stop, not a plain echo.
    shown: List[Tuple[str, str]] = []

    def _capture_show_doc(interp: ConsoleInterpreter) -> None:
        interp.show_doc = lambda title, markdown, *, scroll_to=None: shown.append((title, markdown))  # type: ignore[method-assign]

    _run_debug(STEP_SUITE, [".kw Log", ".continue"], stop_on_entry=True, prepare=_capture_show_doc)
    # title is exactly "Log" for the keyword page; the search-fallback would be
    # "Keywords matching 'Log'", so equality pins the doc-viewer path.
    assert any(title == "Log" for title, _ in shown)


def test_debugger_command_without_stop_reports_not_at_breakpoint() -> None:
    # The debugger commands exist at the shell prompt too (one unified set), but
    # the navigation/resume ones need a stop to act on.
    app = _CaptureApp()
    interpreter = ConsoleInterpreter(app=app)
    controller = DebugController()
    controller.set_frontend(interpreter)
    interpreter.set_controller(controller)
    try:
        interpreter._dispatch_dot_command(".continue")
        interpreter._dispatch_dot_command(".where")
        interpreter._dispatch_dot_command(".break Login")  # breakpoint cmds work without a stop
    finally:
        LOGGER.unregister_logger(interpreter._logger)
    text = "\n".join(app.messages)
    assert text.count("not at a breakpoint") == 2  # .continue and .where
    assert "breakpoint 1 at keyword 'Login'" in text
    assert "Login" in controller.keyword_breakpoints


def test_exit_at_stop_guides_instead_of_leaving() -> None:
    # `.exit`/`.quit` leave the REPL at the shell prompt; at a debug stop that's
    # ambiguous, so it points at the resume/abort commands rather than raising.
    messages = _run_debug(STEP_SUITE, [".exit", ".continue"], stop_on_entry=True)
    text = "\n".join(messages)
    assert "at a debug stop" in text
    assert ".abort" in text
    assert not any("EOFError" in m for m in messages)


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="result.name is only deprecated on Robot Framework >= 7")
def test_repl_marker_check_does_not_read_deprecated_result_name() -> None:
    # The marker check runs on every body-item start, including control
    # structures (RETURN, FOR, …) whose `result.name` RF>=7 deprecates. It must
    # decide via `full_name` only and never touch the deprecated `.name`, or a
    # UserWarning leaks into the debug output.
    class _ControlResult:
        full_name = None  # control structures expose no full_name

        @property
        def name(self) -> str:
            raise AssertionError("must not read the deprecated result.name on RF>=7")

    interpreter = ConsoleInterpreter(app=None)
    try:
        assert interpreter._is_repl_marker(cast(Any, _ControlResult())) is False
    finally:
        LOGGER.unregister_logger(interpreter._logger)


# ---------------------------------------------------------------------------
# Phase 5 — pdb alignment
# ---------------------------------------------------------------------------

# Cluster 1 — alias cleanup (pdb-pure: one long name + one short letter)


def test_return_replaces_stepout_aliases() -> None:
    interp = _bare_interpreter()
    assert interp._resolve_dot_command("return") == ("_return", None)
    assert interp._resolve_dot_command("r") == ("_return", None)
    # the old gdb-style step-out names are gone
    for gone in ("stepout", "finish", "o"):
        attr, error = interp._resolve_dot_command(gone)
        assert attr is None
        assert error is not None


def test_where_drops_backtrace_aliases() -> None:
    interp = _bare_interpreter()
    assert interp._resolve_dot_command("where") == ("_where", None)
    assert interp._resolve_dot_command("w") == ("_where", None)
    for gone in ("bt", "backtrace"):
        attr, error = interp._resolve_dot_command(gone)
        assert attr is None
        assert error is not None


RETURN_SUITE = """\
*** Keywords ***
Inner
    Log    inner

Wrapper
    Inner
    Log    after

*** Test Cases ***
T
    Wrapper
    Log    last
"""


def test_return_steps_out_to_outer_frame() -> None:
    # Stop deep in `Inner`; `.return` runs until `Inner` *and* its caller
    # `Wrapper` have returned, landing on the next sibling of `Wrapper` (`Log
    # last`) — it skips `Inner`'s body and the rest of `Wrapper`'s body.
    messages = _run_debug(RETURN_SUITE, [".return", ".continue"], keyword_breakpoints=["Inner"])
    stops = _stop_lines(messages)
    assert len(stops) == 2
    assert stops[0].startswith("* breakpoint")
    assert "Inner" in stops[0]
    assert stops[1].startswith("* step")
    assert "Log" in stops[1]


# Cluster 4 — .until (stop at a later line in the current frame, or on return)


def test_until_aliases_resolve_by_prefix() -> None:
    interp = _bare_interpreter()
    assert interp._resolve_dot_command("until") == ("_until", None)
    assert interp._resolve_dot_command("unt")[0] == "_until"  # pdb short form, via prefix


def test_until_advances_to_later_line_in_frame() -> None:
    # From the entry stop at `Log before` (line 11), `.until` runs to the next
    # line in the same frame — `Outer` (line 12).
    messages = _run_debug(STEP_SUITE, [".until", ".continue"], stop_on_entry=True)
    stops = _stop_lines(messages)
    assert len(stops) == 2
    assert stops[0].startswith("* entry")
    assert stops[1].startswith("* step")
    assert "Outer" in stops[1]


# Cluster 2 — .whatis / .pprint / .display


def test_whatis_shows_type_not_value() -> None:
    messages = _run_debug(
        VAR_SUITE, [".up", ".whatis ${a}", ".whatis ${a} + ${b}", ".continue"], keyword_breakpoints=["Log"]
    )
    text = "\n".join(messages)
    assert "${a}: str" in text  # bare reference → raw value is a string
    assert "${a} + ${b}: int" in text  # expression → evaluated to int


def test_pprint_formats_value_without_name_prefix() -> None:
    messages = _run_debug(LIST_SUITE, [".up", ".pprint ${items}", ".continue"], keyword_breakpoints=["Log"])
    # `.print` would echo `${items} = [...]`; `.pprint` emits the bare pformat.
    assert "[10, 20, 30]" in messages


DISPLAY_SUITE = """\
*** Variables ***
${V}    hello

*** Test Cases ***
T
    Log    one
    Log    two
"""


def test_display_persists_across_subsequent_stops() -> None:
    messages = _run_debug(DISPLAY_SUITE, [".display ${V}", ".next", ".continue"], stop_on_entry=True)
    text = "\n".join(messages)
    assert "displaying ${V}" in text  # registration echo
    # shown at the *next* stop (the entry stop happened before `.display`)
    assert sum("${V} = 'hello'" in m for m in messages) == 1


def test_undisplay_removes_expression() -> None:
    messages = _run_debug(DISPLAY_SUITE, [".display ${V}", ".undisplay ${V}", ".next", ".continue"], stop_on_entry=True)
    text = "\n".join(messages)
    assert "no longer displaying ${V}" in text
    assert not any("${V} = 'hello'" in m for m in messages)  # never shown after undisplay


# Cluster 3 — .list / .source (shared ±5 source-window renderer)


def test_list_renders_source_window_at_stop() -> None:
    Path(_SOURCE).write_text(STEP_SUITE, encoding="utf-8")
    messages = _run_debug(STEP_SUITE, [".list", ".continue"], stop_on_entry=True)
    marked = [m for m in messages if m.lstrip().startswith("->")]
    assert len(marked) == 1  # exactly the current line is marked
    assert "Log" in marked[0]
    assert "before" in marked[0]
    assert any("Outer" in m for m in messages)  # the ±5 window includes line 12


def test_source_renders_named_keyword_window() -> None:
    # `.source Log` resolves the library keyword and renders its definition
    # window from the BuiltIn Python source (same renderer as `.list`).
    messages = _run_debug(STEP_SUITE, [".source Log", ".continue"], stop_on_entry=True)
    assert any(m.startswith("Log  (") and ".py:" in m for m in messages)  # header with location
    assert any(m.lstrip().startswith("->") for m in messages)  # the definition line is marked


def _source_window_count(messages: List[str]) -> int:
    # Count the numbered source lines (`-> 12  …` / `   13  …`) the inline
    # `.source`/`.list` window emits.
    return sum(1 for m in messages if (s := m.lstrip()) and (s.startswith("->") or s[:1].isdigit()))


def test_source_count_arg_limits_inline_window() -> None:
    # Plain backend: a trailing count sets how many lines are shown from the
    # definition (default 10).
    default = _run_debug(STEP_SUITE, [".source Log", ".continue"], stop_on_entry=True)
    assert _source_window_count(default) == 10
    limited = _run_debug(STEP_SUITE, [".source Log 3", ".continue"], stop_on_entry=True)
    assert _source_window_count(limited) == 3


def test_source_opens_scrollable_viewer_when_available() -> None:
    # prompt_toolkit backend: `.source` loads the WHOLE file into the scrollable
    # doc viewer, marks the definition line, and opens scrolled to it.
    shown: List[Tuple[str, str, Optional[str]]] = []

    def _enable_viewer(interp: ConsoleInterpreter) -> None:
        interp.has_scrollable_viewer = True
        interp.show_doc = lambda title, markdown, *, scroll_to=None: shown.append(  # type: ignore[method-assign]
            (title, markdown, scroll_to)
        )

    messages = _run_debug(STEP_SUITE, [".source Log", ".continue"], stop_on_entry=True, prepare=_enable_viewer)
    assert shown, "the viewer was not opened"
    title, md, scroll_to = shown[0]
    assert title.startswith("Log  (")
    assert ".py:" in title
    assert "```" in md  # source rendered in a code fence
    assert "   1  " in md  # the WHOLE file is loaded (line 1 present), not just a window
    assert "->" in md  # the definition line is marked
    assert scroll_to is not None  # opens scrolled to the marked line
    assert scroll_to.startswith("->")
    # nothing printed inline through the window in viewer mode
    assert _source_window_count(messages) == 0


def test_list_opens_scrollable_viewer_when_available() -> None:
    # prompt_toolkit backend: `.list` loads the WHOLE file into the scrollable
    # viewer and opens scrolled to the current stop line (marked).
    Path(_SOURCE).write_text(STEP_SUITE, encoding="utf-8")
    shown: List[Tuple[str, str, Optional[str]]] = []

    def _enable_viewer(interp: ConsoleInterpreter) -> None:
        interp.has_scrollable_viewer = True
        interp.show_doc = lambda title, markdown, *, scroll_to=None: shown.append(  # type: ignore[method-assign]
            (title, markdown, scroll_to)
        )

    messages = _run_debug(STEP_SUITE, [".list", ".continue"], stop_on_entry=True, prepare=_enable_viewer)
    assert shown, "the viewer was not opened"
    _title, md, scroll_to = shown[0]
    assert "```" in md
    assert "   1  " in md  # whole file loaded, not a ±5 window
    assert "->" in md  # the current line is marked
    assert scroll_to is not None
    assert scroll_to.startswith("->")
    assert _source_window_count(messages) == 0  # nothing inline in viewer mode


def test_source_unknown_keyword_reports() -> None:
    messages = _run_debug(STEP_SUITE, [".source Nonexistent Keyword", ".continue"], stop_on_entry=True)
    assert any("not found" in m for m in messages)


# Cluster 5 — conditional / temporary / ignore / delete / disable breakpoints


COND_SUITE = """\
*** Test Cases ***
T
    FOR    ${i}    IN RANGE    3
        Log    ${i}
    END
"""


def test_conditional_breakpoint_stops_only_when_true() -> None:
    def add_cond(interp: ConsoleInterpreter) -> None:
        interp._controller.add_keyword_breakpoint("Log", condition="${i} == 1")  # type: ignore[union-attr]

    messages = _run_debug(COND_SUITE, [".continue"], prepare=add_cond)
    stops = _stop_lines(messages)
    # `Log` runs three times (i=0,1,2); the condition is true only for i==1.
    assert sum(s.startswith("* breakpoint") for s in stops) == 1


def test_condition_error_still_stops() -> None:
    # A failing condition (undefined variable) stops anyway, so the breakage is
    # noticed rather than silently swallowed (pdb semantics).
    def add_bad(interp: ConsoleInterpreter) -> None:
        interp._controller.add_keyword_breakpoint("Outer", condition="${nonexistent} > 0")  # type: ignore[union-attr]

    messages = _run_debug(STEP_SUITE, [".continue"], prepare=add_bad)
    stops = _stop_lines(messages)
    assert any(s.startswith("* breakpoint") and "Outer" in s for s in stops)


def test_tbreak_is_removed_after_first_hit() -> None:
    # `Log` is hit three times in STEP_SUITE; a temporary breakpoint stops once.
    messages = _run_debug(STEP_SUITE, [".tbreak Log", ".continue", ".continue"], stop_on_entry=True)
    stops = _stop_lines(messages)
    assert sum(s.startswith("* breakpoint") for s in stops) == 1


def test_ignore_skips_next_n_hits() -> None:
    # The entry stop is already on the first `Log` (`Log before`); after
    # resuming, `Log` fires twice more (`Log inner`, `Log outer`). Ignoring the
    # next one skips `Log inner` and stops on `Log outer`.
    messages = _run_debug(STEP_SUITE, [".break Log", ".ignore 1 1", ".continue", ".continue"], stop_on_entry=True)
    stops = _stop_lines(messages)
    assert sum(s.startswith("* breakpoint") for s in stops) == 1


def test_delete_removes_breakpoint() -> None:
    messages = _run_debug(STEP_SUITE, [".break Outer", ".delete 1", ".continue"], stop_on_entry=True)
    stops = _stop_lines(messages)
    assert sum(s.startswith("* breakpoint") for s in stops) == 0  # deleted → never fires


def test_disable_then_enable_breakpoint() -> None:
    disabled = _run_debug(STEP_SUITE, [".break Outer", ".disable 1", ".continue"], stop_on_entry=True)
    assert sum(s.startswith("* breakpoint") for s in _stop_lines(disabled)) == 0

    enabled = _run_debug(
        STEP_SUITE, [".break Outer", ".disable 1", ".enable 1", ".continue", ".continue"], stop_on_entry=True
    )
    assert sum(s.startswith("* breakpoint") for s in _stop_lines(enabled)) == 1


def test_breakpoints_listing_shows_numbers_and_attributes() -> None:
    messages = _run_debug(
        STEP_SUITE,
        [".break Outer, ${x} > 0", ".tbreak Inner", ".ignore 1 3", ".disable 2", ".breakpoints", ".continue"],
        stop_on_entry=True,
    )
    text = "\n".join(messages)
    assert "#1  keyword Outer" in text
    assert "if ${x} > 0" in text
    assert "ignore 3" in text
    assert "#2  keyword Inner" in text
    assert "temp" in text
    assert "disabled" in text


def test_logpoint_logs_and_continues() -> None:
    # A logpoint (log_message set) logs at the hit and keeps running — never
    # stops. This is the shared core DAP `logMessage` reuses.
    def add_logpoint(interp: ConsoleInterpreter) -> None:
        interp._controller.add_keyword_breakpoint("Outer", log_message="hit outer")  # type: ignore[union-attr]

    messages = _run_debug(STEP_SUITE, [], prepare=add_logpoint)
    stops = _stop_lines(messages)
    assert sum(s.startswith("* breakpoint") for s in stops) == 0
    assert "hit outer" in messages


# Cluster 6 — .commands (sub-prompt collection, replayed at each hit)


def test_commands_requires_breakpoint_number() -> None:
    messages = _run_debug(STEP_SUITE, [".commands", ".continue"], stop_on_entry=True)
    assert any("usage: .commands" in m for m in messages)


def test_commands_replay_silent_and_resume() -> None:
    # Attach `silent` + `.where` + `.continue` to the Outer breakpoint. At the
    # hit: the banner is suppressed (silent), `.where` replays, and the trailing
    # `.continue` resumes without consuming an interactive prompt line.
    messages = _run_debug(
        STEP_SUITE,
        [".break Outer", ".commands 1", "silent", ".where", ".continue", "end", ".continue"],
        stop_on_entry=True,
    )
    text = "\n".join(messages)
    stops = _stop_lines(messages)
    assert "breakpoint 1: 3 command(s)" in text  # collection echo (silent counts)
    assert sum(s.startswith("* breakpoint") for s in stops) == 0  # Outer hit was silent
    assert "#0  Outer" in text  # the replayed `.where` ran at the hit


# ---------------------------------------------------------------------------
# Phase 5 — coverage follow-ups (audit gaps): error paths, bare forms, feature
# interactions, prefix-collision resolution, help listing.
# ---------------------------------------------------------------------------

# Cluster 2 — inspection error/edge paths


def test_whatis_and_pprint_surface_evaluate_errors() -> None:
    # An unresolvable variable surfaces a `! <err>` line (same path as `.print`).
    messages = _run_debug(
        STEP_SUITE, [".whatis ${nonexistent}", ".pprint ${nonexistent}", ".continue"], stop_on_entry=True
    )
    assert sum(1 for m in messages if m.startswith("! ")) >= 2


def test_bare_display_shows_values_when_stopped() -> None:
    messages = _run_debug(DISPLAY_SUITE, [".display ${V}", ".display", ".continue"], stop_on_entry=True)
    # bare `.display` while stopped re-evaluates the registered exprs
    assert any(m == "${V} = 'hello'" for m in messages)


def test_bare_display_lists_expressions_when_not_stopped() -> None:
    app = _CaptureApp()
    interp = ConsoleInterpreter(app=app)
    interp._display_exprs.append("${X}")
    try:
        interp._dispatch_dot_command(".display")  # not at a stop -> list the raw exprs
    finally:
        LOGGER.unregister_logger(interp._logger)
    assert "${X}" in app.messages


def test_display_error_does_not_abort_stop_render() -> None:
    messages = _run_debug(DISPLAY_SUITE, [".display ${nonexistent}", ".next", ".continue"], stop_on_entry=True)
    # the failing display is reported inline...
    assert any(m.startswith("${nonexistent} = ! ") for m in messages)
    # ...and the stop banner still renders (entry + the `.next` step stop)
    assert sum(1 for m in messages if m.startswith("* ")) >= 2


def test_display_evaluates_against_selected_frame() -> None:
    # ${a} is a local of the enclosing `Add` keyword, not the inner `Log` frame;
    # bare `.display` after `.up` evaluates against the selected (Add) frame.
    messages = _run_debug(VAR_SUITE, [".up", ".display ${a}", ".display", ".continue"], keyword_breakpoints=["Log"])
    assert any(m == "${a} = '2'" for m in messages)


# Cluster 3 — .source variants


def test_source_suite_local_keyword_not_resolved() -> None:
    # Known limitation: `.source` resolves keywords from imported libraries and
    # resources (see the BuiltIn `Log` and resource tests), but NOT keywords
    # defined in the running suite file itself — `lookup_keyword_owner` does not
    # enumerate the executing suite's own keywords, so it reports "not found".
    Path(_SOURCE).write_text(STEP_SUITE, encoding="utf-8")
    messages = _run_debug(STEP_SUITE, [".source Outer", ".continue"], stop_on_entry=True)
    assert any("keyword 'Outer' not found" in m for m in messages)


def test_source_resource_keyword(tmp_path: Path) -> None:
    res = tmp_path / "kw.resource"
    res.write_text("*** Keywords ***\nCustom Step\n    Log    hi\n", encoding="utf-8")
    # Forward slashes: a raw Windows path (backslashes) in .robot source would be
    # mangled by Robot's escape handling, so the resource import would fail.
    suite_text = f"*** Settings ***\nResource    {res.as_posix()}\n\n*** Test Cases ***\nT\n    Custom Step\n"
    messages = _run_debug(suite_text, [".source Custom Step", ".continue"], stop_on_entry=True)
    assert any(m.startswith("Custom Step  (") and "kw.resource:" in m for m in messages)
    assert any(m.lstrip().startswith("->") for m in messages)


def test_source_without_line_reports_no_source(monkeypatch: "pytest.MonkeyPatch") -> None:
    import types

    from robotcode.repl import console_interpreter as ci

    def _no_line_doc(*a: object, **k: object) -> object:
        return types.SimpleNamespace(source="/x.py", line_no=None)

    monkeypatch.setattr(ci, "_diagnostics_keyword_doc", _no_line_doc)
    messages = _run_debug(STEP_SUITE, [".source Log", ".continue"], stop_on_entry=True)
    assert any("(no source available for" in m for m in messages)


# Cluster 5 — bare forms, reference errors, condition set/clear, tbreak+condition


def test_bare_delete_removes_all_breakpoints() -> None:
    messages = _run_debug(STEP_SUITE, [".break Outer", ".break Inner", ".delete", ".continue"], stop_on_entry=True)
    assert any("removed 2 breakpoint(s)" in m for m in messages)
    assert sum(s.startswith("* breakpoint") for s in _stop_lines(messages)) == 0


def test_bare_disable_disables_all_breakpoints() -> None:
    messages = _run_debug(STEP_SUITE, [".break Outer", ".break Inner", ".disable", ".continue"], stop_on_entry=True)
    assert any("all breakpoints disabled" in m for m in messages)
    assert sum(s.startswith("* breakpoint") for s in _stop_lines(messages)) == 0


def test_breakpoint_reference_errors() -> None:
    messages = _run_debug(STEP_SUITE, [".delete abc", ".delete 99", ".continue"], stop_on_entry=True)
    text = "\n".join(messages)
    assert "not a breakpoint number: abc" in text
    assert "no breakpoint 99" in text


def test_condition_command_sets_then_clears() -> None:
    # Setting a condition gates the breakpoint to the truthy iteration only.
    gated = _run_debug(
        COND_SUITE, [".break Log", ".condition 1 ${i} == 1", ".continue", ".continue"], stop_on_entry=True
    )
    assert "breakpoint 1: condition ${i} == 1" in "\n".join(gated)
    assert sum(s.startswith("* breakpoint") for s in _stop_lines(gated)) == 1
    # Clearing it echoes the cleared message.
    cleared = _run_debug(
        COND_SUITE,
        [".break Log", ".condition 1 ${i} == 1", ".condition 1", ".continue", ".continue", ".continue", ".continue"],
        stop_on_entry=True,
    )
    assert "breakpoint 1: condition cleared" in "\n".join(cleared)


def test_tbreak_with_condition_fires_once() -> None:
    # A one-shot conditional breakpoint: skips i==0 (false), fires once at i==1,
    # is removed, so i==2 never stops.
    messages = _run_debug(COND_SUITE, [".tbreak Log, ${i} == 1", ".continue", ".continue"], stop_on_entry=True)
    assert sum(s.startswith("* breakpoint") for s in _stop_lines(messages)) == 1


# Cluster 6 — .commands edge cases


def test_commands_empty_collection_clears_attached_list() -> None:
    messages = _run_debug(
        STEP_SUITE,
        [
            ".break Outer",
            ".commands 1",
            "silent",
            ".continue",
            "end",  # attach [silent, .continue]
            ".commands 1",
            "end",  # immediate end -> clear
            ".continue",  # resume entry
            ".continue",  # resume the now-interactive Outer hit
        ],
        stop_on_entry=True,
    )
    assert "breakpoint 1: commands cleared" in "\n".join(messages)
    # commands gone -> Outer stops interactively (banner shown again)
    assert any(s.startswith("* breakpoint") and "Outer" in s for s in _stop_lines(messages))


def test_commands_without_resume_falls_through_to_prompt() -> None:
    messages = _run_debug(
        STEP_SUITE,
        [".break Outer", ".commands 1", ".where", "end", ".continue", ".continue"],
        stop_on_entry=True,
    )
    text = "\n".join(messages)
    assert "#0  Outer" in text  # the attached `.where` replayed at the hit
    # no resuming command attached -> the interactive prompt ran (banner shown)
    assert any(s.startswith("* breakpoint") and "Outer" in s for s in _stop_lines(messages))


def test_commands_short_circuit_after_resuming_command() -> None:
    # commands = [silent, .continue, .where]; `.continue` resumes, so the
    # trailing `.where` is skipped (never renders the stack).
    messages = _run_debug(
        STEP_SUITE,
        [".break Outer", ".commands 1", "silent", ".continue", ".where", "end", ".continue"],
        stop_on_entry=True,
    )
    assert "#0  Outer" not in "\n".join(messages)


def test_commands_eof_during_collection_commits_partial() -> None:
    # Reader EOFs before `end`: whatever was collected so far is committed.
    messages = _run_debug(STEP_SUITE, [".break Outer", ".commands 1", "silent"], stop_on_entry=True)
    assert any("breakpoint 1: 1 command(s)" in m for m in messages)


# Cluster 1 follow-up — prefix-abbreviation collisions among the new commands


def test_phase5_prefix_collisions_report_ambiguity() -> None:
    interp = _bare_interpreter()
    cases = [
        ("un", (".undisplay", ".until")),
        ("de", (".delete", ".detach")),
        ("di", (".disable", ".display")),
        ("e", (".enable", ".exit")),
        ("con", (".condition", ".continue")),
        ("i", (".ignore", ".imports")),  # cross-group (Debugger + Session)
    ]
    for prefix, names in cases:
        attr, error = interp._resolve_dot_command(prefix)
        assert attr is None, prefix
        assert error is not None, prefix
        for name in names:
            assert name in error, (prefix, name)
    # disambiguating extensions still resolve uniquely
    assert interp._resolve_dot_command("unt") == ("_until", None)
    assert interp._resolve_dot_command("und") == ("_undisplay", None)
    assert interp._resolve_dot_command("del") == ("_delete", None)
    assert interp._resolve_dot_command("det") == ("_detach", None)
    assert interp._resolve_dot_command("disp") == ("_display", None)
    assert interp._resolve_dot_command("en") == ("_enable", None)
    assert interp._resolve_dot_command("com") == ("_commands", None)


# .help — the Phase-5 commands are listed and have per-command detail pages


def test_help_lists_phase5_commands_and_shows_detail() -> None:
    app = _CaptureApp()
    interp = ConsoleInterpreter(app=app)
    shown: List[Tuple[str, str]] = []
    interp.show_doc = lambda title, markdown, *, scroll_to=None: shown.append((title, markdown))  # type: ignore[method-assign]
    try:
        interp._dispatch_dot_command(".help")
        interp._dispatch_dot_command(".help until")
    finally:
        LOGGER.unregister_logger(interp._logger)
    body = next(markdown for title, markdown in shown if title == "Dot-commands")
    for cmd in (".until", ".return", ".display", ".tbreak", ".condition", ".commands", ".source"):
        assert cmd in body
    until_pages = [markdown for title, markdown in shown if title == ".until"]
    assert until_pages  # `.help until` opened the per-command detail page
    assert "later line in the current frame" in until_pages[0]


# ---------------------------------------------------------------------------
# `.debug on|off` — attach / detach the debugger from the >>> prompt
# ---------------------------------------------------------------------------


def _debug_interp() -> "tuple[ConsoleInterpreter, DebugController, _CaptureApp]":
    app = _CaptureApp()
    interp = ConsoleInterpreter(app=app)
    controller = DebugController()
    interp.set_controller(controller)
    return interp, controller, app


def test_debug_on_off_attaches_and_detaches() -> None:
    interp, controller, _ = _debug_interp()
    interp._dispatch_dot_command(".debug off")
    assert controller.attached is False
    interp._dispatch_dot_command(".debug on")
    assert controller.attached is True


def test_debug_bare_shows_attached_state() -> None:
    interp, _, app = _debug_interp()
    interp._dispatch_dot_command(".debug")  # a fresh controller is attached
    assert any("debugger: attached" in m for m in app.messages)
    app.messages.clear()
    interp._dispatch_dot_command(".debug off")
    app.messages.clear()
    interp._dispatch_dot_command(".debug")
    assert any("debugger: detached" in m for m in app.messages)


def test_debug_off_preserves_breakpoints_and_catch_filters() -> None:
    # Detaching must NOT discard configuration, so a later `.debug on` resumes
    # with the same breakpoints and `.catch` filters still in place.
    interp, controller, _ = _debug_interp()
    controller.set_exception_breakpoints(["failed_test"])
    controller.set_keyword_breakpoints(["Open Browser"])
    interp._dispatch_dot_command(".debug off")
    assert controller.exception_filters == {"failed_test"}
    assert controller.keyword_breakpoints == {"Open Browser"}
    interp._dispatch_dot_command(".debug on")  # re-attach keeps the same config
    assert controller.exception_filters == {"failed_test"}
    assert controller.keyword_breakpoints == {"Open Browser"}


def test_detach_command_is_non_destructive() -> None:
    # The `.detach` command detaches and resumes the run, but (like `.debug off`)
    # KEEPS the configured breakpoints/filters — so a later `.debug on` resumes
    # with the same setup. It also disables further stops for this run.
    holder: "dict[str, DebugController]" = {}

    def grab(interp: ConsoleInterpreter) -> None:
        assert interp._controller is not None
        holder["controller"] = interp._controller

    messages = _run_debug(STEP_SUITE, [".detach"], stop_on_entry=True, keyword_breakpoints=["Outer"], prepare=grab)
    controller = holder["controller"]
    assert controller.attached is False
    # config survived the detach (non-destructive contract)...
    assert controller.keyword_breakpoints == {"Outer"}
    # ...yet the later `Outer` breakpoint never fired (detached silences stops)
    assert not any(s.startswith("* breakpoint") for s in _stop_lines(messages))


def test_debug_unknown_arg_shows_usage() -> None:
    interp, _, app = _debug_interp()
    interp._dispatch_dot_command(".debug bogus")
    assert any("usage: .debug" in m for m in app.messages)


# ---------------------------------------------------------------------------
# A detached controller silences pauses (incl. exceptions) without losing config
# ---------------------------------------------------------------------------

FAIL_SUITE = """\
*** Test Cases ***
T
    Log    before
    Fail    boom
    Log    after
"""


def test_attached_controller_stops_on_uncaught_failure() -> None:
    # Sanity baseline: armed + attached → the uncaught failure pauses.
    messages = _run_debug(FAIL_SUITE, [".continue", ".continue"], exception_filters=["uncaught_failed_keyword"])
    assert any(m.startswith("* exception") for m in _stop_lines(messages))


def test_detached_controller_does_not_stop_on_failure() -> None:
    # Armed to break on uncaught failures, but detached → nothing pauses, even
    # though the filter stays set (the non-destructive detach contract).
    def detach(interp: ConsoleInterpreter) -> None:
        assert interp._controller is not None
        interp._controller.set_attached(False)

    messages = _run_debug(
        FAIL_SUITE, [".continue", ".continue"], exception_filters=["uncaught_failed_keyword"], prepare=detach
    )
    assert not any(m.startswith("* exception") for m in messages)


def test_setting_alias_does_not_fire_at_rdb_prompt() -> None:
    # The `Library`/`Resource`/`Variables` setting aliases are a >>>-prompt-only
    # convenience. At the (rdb) prompt `Library    Collections` must be evaluated
    # as an ordinary keyword (and fail as unknown), NOT rewritten to `Import
    # Library` — which would otherwise silently import the library.
    messages = _run_debug(STEP_SUITE, ["Library    Collections", ".continue"], stop_on_entry=True)
    assert any("No keyword with name 'Library'" in m for m in messages)


def test_debug_off_at_a_live_stop_resumes_without_further_pauses() -> None:
    # The interactive path the redesign is for: armed to break on BOTH the
    # uncaught failure and the failing test, pause at the first (rdb) stop, type
    # `.debug off` to detach, then `.continue` — the test-end stop that would
    # otherwise fire is suppressed, so exactly one stop occurs and the run ends.
    messages = _run_debug(
        FAIL_SUITE,
        [".debug off", ".continue", ".continue"],
        exception_filters=["uncaught_failed_keyword", "failed_test"],
    )
    assert len(_stop_lines(messages)) == 1
