"""Click-level tests for `robotcode repl` flags.

Focused on flag parsing and translation — the interpreter itself is
mocked out so the test never starts a real prompt session.
"""

from pathlib import Path
from typing import Any, Dict, List, Set

import pytest
from click.testing import CliRunner

from robotcode.plugin._agent_detection import _AGENT_ENV_VARS
from robotcode.repl import cli as cli_mod


@pytest.fixture(autouse=True)
def _scrub_agent_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every known agent marker so the suite behaves the same when
    run inside Claude Code (CLAUDECODE=1 set by the agent) as it does in
    a plain shell. Individual tests that need the agent path active set
    the relevant var via monkeypatch.setenv."""
    for var in (*_AGENT_ENV_VARS, "ROBOTCODE_FORCE_AI_AGENT", "ROBOTCODE_NO_AI_AGENT"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def capture_interpreter_kwargs(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """Patch `_pick_interpreter` + `run_repl` so the test never enters a
    real prompt loop. The dict the fixture returns receives the kwargs
    the CLI passed to the factory — `backend` and friends."""
    captured: Dict[str, Any] = {}

    class _DummyInterpreter:
        # `shell` attaches the debugger, which sets the controller, registers it
        # as an observer, and builds a debug-prompt completer via `make_completer`.
        def read_line(self, prompt: str, **kwargs: Any) -> str:
            return ""

        def register_observer(self, observer: Any) -> None:
            pass

        def set_controller(self, controller: Any) -> None:
            pass

        def make_completer(self, command_names: Any, context_provider: Any) -> Any:
            return None

    def fake_pick(**kwargs: Any) -> _DummyInterpreter:
        captured.update(kwargs)
        return _DummyInterpreter()

    monkeypatch.setattr(cli_mod, "_pick_interpreter", fake_pick)
    monkeypatch.setattr(cli_mod, "run_repl", lambda **_: None)
    # Simulate an interactive terminal so these tests exercise the auto/agent/
    # explicit backend logic rather than the non-TTY fallback (CliRunner's stdin
    # is itself non-interactive). The non-TTY path has its own test below.
    monkeypatch.setattr(cli_mod, "_is_interactive_stdin", lambda: True)
    return captured


def test_cli_backend_default_is_auto(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    # Interactive terminal (simulated by the fixture): the default stays `auto`.
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "auto"


def test_cli_backend_non_tty_default_falls_back_to_plain(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Piped/redirected stdin can't drive prompt_toolkit — the default `auto`
    # resolves to `plain` (reads until EOF) so `echo … | robotcode repl` works.
    monkeypatch.setattr(cli_mod, "_is_interactive_stdin", lambda: False)
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "plain"


def test_cli_explicit_prompt_toolkit_kept_even_on_non_tty(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # An explicit `--backend prompt-toolkit` is the user's call — not overridden
    # by the non-TTY fallback (which only applies to `auto`).
    monkeypatch.setattr(cli_mod, "_is_interactive_stdin", lambda: False)
    result = CliRunner().invoke(cli_mod.repl, ["--backend", "prompt-toolkit"])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "prompt-toolkit"


def test_cli_backend_explicit_value_passed_through(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    result = CliRunner().invoke(cli_mod.repl, ["--backend", "prompt-toolkit"])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "prompt-toolkit"


def test_cli_plain_translates_to_backend_plain(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    result = CliRunner().invoke(cli_mod.repl, ["--plain"])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "plain"


def test_cli_plain_with_redundant_backend_plain_is_ok(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    """`--plain --backend=plain` is redundant but not a conflict — both
    say the same thing."""
    result = CliRunner().invoke(cli_mod.repl, ["--plain", "--backend", "plain"])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "plain"


def test_cli_plain_with_conflicting_backend_errors(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    del capture_interpreter_kwargs  # the conflict must be detected before the interpreter is built
    result = CliRunner().invoke(cli_mod.repl, ["--plain", "--backend", "prompt-toolkit"])
    assert result.exit_code != 0
    assert "--plain conflicts" in result.output


def test_cli_backend_unknown_value_rejected_by_click(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    del capture_interpreter_kwargs
    result = CliRunner().invoke(cli_mod.repl, ["--backend", "foo"])
    assert result.exit_code != 0
    # click.Choice's error message lists the valid values.
    assert "Invalid value" in result.output or "invalid choice" in result.output.lower()


def test_cli_backend_env_var_picked_up(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROBOTCODE_REPL_BACKEND", "prompt-toolkit")
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "prompt-toolkit"


# ---------------------------------------------------------------------------
# AI-agent auto-detect — flips `auto` to `plain` so agents get clean output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("marker", ["CLAUDECODE", "CURSOR_AGENT", "OPENCODE", "AGENT", "CODEX_CI"])
def test_cli_agent_marker_flips_backend_to_plain(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch, marker: str
) -> None:
    """A representative set of agent markers — each should flip the
    default backend to `plain` without the user passing `--plain`."""
    monkeypatch.setenv(marker, "1" if marker != "AGENT" else "goose")
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "plain"


def test_cli_explicit_backend_beats_agent_detection(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    result = CliRunner().invoke(cli_mod.repl, ["--backend", "prompt-toolkit"])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "prompt-toolkit"


def test_cli_repl_backend_env_var_beats_agent_detection(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("ROBOTCODE_REPL_BACKEND", "prompt-toolkit")
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "prompt-toolkit"


def test_cli_repl_plain_env_var_satisfies_agent_path(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ROBOTCODE_REPL_PLAIN=1` already does the right thing; the agent
    branch must not overwrite it (would be a no-op here, but the test
    pins the precedence in case `plain` ever means something else)."""
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("ROBOTCODE_REPL_PLAIN", "1")
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "plain"


def test_cli_no_ai_agent_override_disables_detection(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("ROBOTCODE_NO_AI_AGENT", "1")
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "auto"


def test_cli_force_ai_agent_override_enables_detection(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Useful for local repros of agent-mode bugs without an actual agent running."""
    monkeypatch.setenv("ROBOTCODE_FORCE_AI_AGENT", "1")
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "plain"


# ---------------------------------------------------------------------------
# `repl` (alias `shell`) is a flat command — bare/file/options run the shell
# (above). `robot-debug` (alias `run-debug`) runs a real suite via the runner
# with the debugger attached. Both are top-level AliasedCommands.
# ---------------------------------------------------------------------------


@pytest.fixture
def capture_robot_delegation(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """Replace the runner's `robot` command so `robot-debug` doesn't actually
    execute a suite; capture the args it would forward."""
    captured: Dict[str, Any] = {}

    class _FakeRobot:
        def make_context(self, info_name: str, args: Any, parent: Any = None) -> Any:
            captured["args"] = list(args)
            return object()

        def invoke(self, ctx: Any) -> None:
            captured["invoked"] = True

    import importlib

    # `robotcode.runner.cli.robot` is shadowed by the re-exported command object,
    # so fetch the actual submodule to patch its `robot` attribute.
    runner_robot = importlib.import_module("robotcode.runner.cli.robot")
    monkeypatch.setattr(runner_robot, "robot", _FakeRobot())
    return captured


def test_robot_debug_forwards_args_to_runner(capture_robot_delegation: Dict[str, Any]) -> None:
    result = CliRunner().invoke(cli_mod.robot_debug, ["-bl", "Suite.Test", "tests/"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    # `robot-debug` forwards args unchanged — no console mode is forced, so the run
    # produces the same output as `robotcode robot`.
    assert capture_robot_delegation["args"] == ["--by-longname", "Suite.Test", "tests/"]


# ---------------------------------------------------------------------------
# debugger attach/detach: `repl` starts detached (unless a trigger or
# `--debugger-attached` is given), `robot-debug` starts attached. Exception
# breaking is armed by default and only fires while attached.
# ---------------------------------------------------------------------------


def _capture_attach_kwargs(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """Wrap (not replace) `_attach_debugger` so the real wiring still runs while
    we record the keyword args the command resolved (`attached`,
    `break_on_exception`, …)."""
    captured: Dict[str, Any] = {}
    real_attach = cli_mod._attach_debugger

    def capturing(interpreter: Any, **kw: Any) -> Any:
        captured.update(kw)
        return real_attach(interpreter, **kw)

    monkeypatch.setattr(cli_mod, "_attach_debugger", capturing)
    return captured


def test_cli_repl_is_detached_by_default(
    monkeypatch: pytest.MonkeyPatch, capture_interpreter_kwargs: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert captured["attached"] is False
    # exception breaking stays armed — it just won't fire until attached
    assert captured["break_on_exception"] is True


def test_cli_repl_debugger_attached_flag(
    monkeypatch: pytest.MonkeyPatch, capture_interpreter_kwargs: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.repl, ["--debugger-attached"])
    assert result.exit_code == 0, result.output
    assert captured["attached"] is True


def test_cli_repl_break_trigger_auto_attaches(
    monkeypatch: pytest.MonkeyPatch, capture_interpreter_kwargs: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.repl, ["--break", "Some Keyword"])
    assert result.exit_code == 0, result.output
    assert captured["attached"] is True


def test_cli_repl_no_debugger_attached_overrides_trigger(
    monkeypatch: pytest.MonkeyPatch, capture_interpreter_kwargs: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.repl, ["--break", "Some Keyword", "--no-debugger-attached"])
    assert result.exit_code == 0, result.output
    assert captured["attached"] is False


def test_cli_repl_break_on_exception_opt_in_auto_attaches(
    monkeypatch: pytest.MonkeyPatch, capture_interpreter_kwargs: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.repl, ["--break-on-exception"])
    assert result.exit_code == 0, result.output
    assert captured["attached"] is True
    assert captured["break_on_exception"] is True


@pytest.mark.parametrize(
    "flag",
    ["--break-on-all-exceptions", "--break-on-failed-test", "--break-on-failed-suite"],
)
def test_cli_repl_break_on_star_flags_auto_attach(
    flag: str, monkeypatch: pytest.MonkeyPatch, capture_interpreter_kwargs: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.repl, [flag])
    assert result.exit_code == 0, result.output
    assert captured["attached"] is True


def test_cli_repl_no_break_on_exception_disarms_and_stays_detached(
    monkeypatch: pytest.MonkeyPatch, capture_interpreter_kwargs: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.repl, ["--no-break-on-exception"])
    assert result.exit_code == 0, result.output
    assert captured["break_on_exception"] is False
    assert captured["attached"] is False


def test_cli_robot_debug_is_attached_by_default(
    monkeypatch: pytest.MonkeyPatch, capture_robot_delegation: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.robot_debug, ["tests/"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert captured["attached"] is True
    assert captured["break_on_exception"] is True


def test_cli_robot_debug_no_debugger_attached_opt_out(
    monkeypatch: pytest.MonkeyPatch, capture_robot_delegation: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.robot_debug, ["--no-debugger-attached", "tests/"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert captured["attached"] is False


def test_cli_robot_debug_no_break_on_exception_disarms_but_stays_attached(
    monkeypatch: pytest.MonkeyPatch, capture_robot_delegation: Dict[str, Any]
) -> None:
    captured = _capture_attach_kwargs(monkeypatch)
    result = CliRunner().invoke(cli_mod.robot_debug, ["--no-break-on-exception", "tests/"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert captured["break_on_exception"] is False
    assert captured["attached"] is True
    assert capture_robot_delegation.get("invoked")


def test_robot_debug_forwards_bare_paths(capture_robot_delegation: Dict[str, Any]) -> None:
    result = CliRunner().invoke(cli_mod.robot_debug, ["tests/"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert capture_robot_delegation["args"] == ["tests/"]


def test_robot_debug_trigger_flags_consumed_not_forwarded(capture_robot_delegation: Dict[str, Any]) -> None:
    """`--break`/`--stop-on-entry`/`--break-on-exception` are our options — they
    must not leak into the args forwarded to the runner."""
    result = CliRunner().invoke(
        cli_mod.robot_debug,
        ["--break", "f.robot:10", "--stop-on-entry", "--break-on-exception", "tests/"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert capture_robot_delegation["args"] == ["tests/"]


# ---------------------------------------------------------------------------
# Exception breakpoints — uncaught breaks by default; each filter is a CLI flag.
# ---------------------------------------------------------------------------


def _attached_exception_filters(**kwargs: Any) -> Set[str]:
    """The exception filters `_attach_debugger` arms for the given flag values."""
    from robot.output import LOGGER

    from robotcode.repl.console_interpreter import ConsoleInterpreter

    interp = ConsoleInterpreter(app=None)
    try:
        return cli_mod._attach_debugger(interp, break_at=(), **kwargs).exception_filters
    finally:
        LOGGER.unregister_logger(interp._logger)


def test_attach_debugger_breaks_on_uncaught_by_default() -> None:
    assert _attached_exception_filters() == {"uncaught_failed_keyword"}


def test_attach_debugger_no_break_on_exception_disables_it() -> None:
    assert _attached_exception_filters(break_on_exception=False) == set()


def test_attach_debugger_optional_exception_filters() -> None:
    assert _attached_exception_filters(
        break_on_all_exceptions=True, break_on_failed_test=True, break_on_failed_suite=True
    ) == {"uncaught_failed_keyword", "failed_keyword", "failed_test", "failed_suite"}


def test_exception_flags_wired_to_attach_debugger(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    # The `--break-on-*` flags reach `_attach_debugger` with the right booleans.
    captured: Dict[str, Any] = {}
    monkeypatch.setattr(cli_mod, "_attach_debugger", lambda interp, **kw: captured.update(kw))
    result = CliRunner().invoke(
        cli_mod.repl, ["--no-break-on-exception", "--break-on-failed-test"], catch_exceptions=False
    )
    assert result.exit_code == 0, result.output
    assert captured["break_on_exception"] is False
    assert captured["break_on_failed_test"] is True
    assert captured["break_on_all_exceptions"] is False
    assert captured["break_on_failed_suite"] is False


def test_top_level_aliases_resolve() -> None:
    # `repl` carries the alias `shell`, `robot-debug` carries `run-debug`; both
    # resolve through the root `robotcode` AliasedGroup.
    from robotcode.cli import robotcode as root

    shell = CliRunner().invoke(root, ["shell", "--help"], catch_exceptions=False)
    assert shell.exit_code == 0, shell.output
    assert "Run Robot Framework interactively" in shell.output

    run_debug = CliRunner().invoke(root, ["run-debug", "--help"], catch_exceptions=False)
    assert run_debug.exit_code == 0, run_debug.output
    assert "Run a real Robot Framework suite" in run_debug.output


def _help_option_flags(help_text: str) -> List[str]:
    """The option flags from a `--help` page, in render order (first token of each
    line that introduces an option)."""
    flags: List[str] = []
    for line in help_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            flags.append(stripped.split()[0].rstrip(","))
    return flags


@pytest.mark.parametrize("command", ["repl", "robot_debug"])
def test_version_is_the_last_option(command: str) -> None:
    # `--version` must render right before `--help` (matching discover/analyze/
    # libdoc), not buried mid-list — guards the option-ordering fix.
    result = CliRunner().invoke(getattr(cli_mod, command), ["--help"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    flags = _help_option_flags(result.output)
    assert flags[-2:] == ["--version", "--help"], flags


# End-to-end: a real suite through the real runner, with the debugger attached
# and the debug prompt fed from stdin. Exercises the whole `robot-debug` wiring
# (interpreter + controller + frontend + forward_events) that the mocked tests
# above bypass.


def test_robot_debug_stop_on_entry_end_to_end(tmp_path: Path) -> None:
    # `--plain`: the debug prompt is a plain `input()` loop the CliRunner can
    # feed (a prompt_toolkit session needs a real terminal).
    suite = tmp_path / "s.robot"
    suite.write_text("*** Test Cases ***\nT\n    Log    hi\n", encoding="utf-8")
    result = CliRunner().invoke(
        cli_mod.robot_debug,
        ["--plain", "--stop-on-entry", "-d", str(tmp_path), str(suite)],
        input=".where\n.continue\n",
    )
    assert result.exit_code == 0, result.output
    assert "* entry" in result.output  # stopped at the first keyword
    assert "#0  BuiltIn.Log" in result.output  # .where rendered the stack with the keyword's full name


def test_robot_debug_abort_aborts_end_to_end(tmp_path: Path) -> None:
    suite = tmp_path / "s.robot"
    suite.write_text("*** Test Cases ***\nT\n    Log    one\n    Log    two\n", encoding="utf-8")
    result = CliRunner().invoke(
        cli_mod.robot_debug,
        ["--plain", "--stop-on-entry", "-d", str(tmp_path), str(suite)],
        input=".abort\n",
    )
    assert "aborting the run" in result.output
    assert result.exit_code != 0  # SystemExit from .abort


def test_robot_debug_breaks_on_uncaught_failure_by_default(tmp_path: Path) -> None:
    # No flags: an uncaught failing keyword pauses the run out of the box.
    suite = tmp_path / "s.robot"
    suite.write_text("*** Test Cases ***\nT\n    Fail    boom\n", encoding="utf-8")
    result = CliRunner().invoke(cli_mod.robot_debug, ["--plain", "-d", str(tmp_path), str(suite)], input=".continue\n")
    assert "* exception" in result.output  # paused on the uncaught failure


def test_robot_debug_no_break_on_exception_runs_through(tmp_path: Path) -> None:
    # With the default disabled, the same failing suite runs to the end unpaused.
    suite = tmp_path / "s.robot"
    suite.write_text("*** Test Cases ***\nT\n    Fail    boom\n", encoding="utf-8")
    result = CliRunner().invoke(
        cli_mod.robot_debug, ["--plain", "--no-break-on-exception", "-d", str(tmp_path), str(suite)]
    )
    assert "* exception" not in result.output


def test_repl_shell_debugger_breaks_on_keyword(tmp_path: Path) -> None:
    # Passing `--break` auto-attaches the otherwise-detached `repl` debugger, so
    # running `Log` at the prompt with that keyword breakpoint set drops into the
    # debug prompt; `.continue` resumes.
    result = CliRunner().invoke(
        cli_mod.repl,
        ["--plain", "--break", "Log", "-d", str(tmp_path)],
        input="Log    hi\n.continue\n\n",
    )
    assert result.exit_code == 0, result.output
    assert "* breakpoint" in result.output
    assert "Log" in result.output


def test_repl_shell_detached_by_default_does_not_break_on_failure(tmp_path: Path) -> None:
    # The headline of the redesign: a bare `repl` (no trigger flags) starts
    # detached, so a failing keyword does NOT drop into the `(rdb)` debugger —
    # an attached session would echo `* exception` / `(rdb)` into the output
    # (as the breakpoint test above shows for `* breakpoint`); here neither
    # appears, and the session exits cleanly after the failure.
    result = CliRunner().invoke(
        cli_mod.repl,
        ["--plain", "-d", str(tmp_path)],
        input="NotARealKeyword123\nLog    after\n\n",
    )
    assert result.exit_code == 0, result.output
    assert "* exception" not in result.output
    assert "(rdb)" not in result.output


def test_robot_debug_translates_debug_terminated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # If the core raises DebugTerminated out of the run, the `robot-debug`
    # driver catches it and reports a clean message instead of crashing. (No
    # console command produces TERMINATE today — this guards the DAP-shared
    # branch from silently rotting.)
    from robotcode.repl._debug import DebugTerminated

    suite = tmp_path / "s.robot"
    suite.write_text("*** Test Cases ***\nT\n    Log    hi\n", encoding="utf-8")

    def _raise_terminated(*args: Any, **kwargs: Any) -> None:
        raise DebugTerminated

    monkeypatch.setattr(cli_mod, "_invoke_runner", _raise_terminated)
    result = CliRunner().invoke(
        cli_mod.robot_debug, ["--plain", "-d", str(tmp_path), str(suite)], catch_exceptions=False
    )
    assert "Debugger: run terminated." in result.output
    assert result.exit_code == 0
