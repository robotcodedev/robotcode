"""Click-level tests for `robotcode repl` flags.

Focused on flag parsing and translation — the interpreter itself is
mocked out so the test never starts a real prompt session.
"""

from typing import Any, Dict, List

import pytest
from click.testing import CliRunner

from robotcode.plugin._agent_detection import _AGENT_ENV_VARS
from robotcode.repl import cli as cli_mod
from robotcode.repl._input import BackendUnavailableError


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
    """Patch `ConsoleInterpreter` + `run_repl` so the test never enters a real
    prompt loop. The dict the fixture returns receives the captured kwargs."""
    captured: Dict[str, Any] = {}

    class _DummyInterpreter:
        def __init__(self, app: Any, **kwargs: Any) -> None:
            del app
            captured.update(kwargs)

    monkeypatch.setattr(cli_mod, "ConsoleInterpreter", _DummyInterpreter)
    monkeypatch.setattr(cli_mod, "run_repl", lambda **_: None)
    return captured


def test_cli_backend_default_is_auto(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "auto"


def test_cli_backend_explicit_value_passed_through(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    result = CliRunner().invoke(cli_mod.repl, ["--backend", "readline"])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "readline"


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
    result = CliRunner().invoke(cli_mod.repl, ["--plain", "--backend", "readline"])
    assert result.exit_code != 0
    assert "--plain conflicts" in result.output


def test_cli_backend_unknown_value_rejected_by_click(capture_interpreter_kwargs: Dict[str, Any]) -> None:
    del capture_interpreter_kwargs
    result = CliRunner().invoke(cli_mod.repl, ["--backend", "foo"])
    assert result.exit_code != 0
    # click.Choice's error message lists the valid values.
    assert "Invalid value" in result.output or "invalid choice" in result.output.lower()


def test_cli_backend_unavailable_translates_to_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the interpreter can't load the requested backend, the CLI
    surfaces it as a usage error with the original install hint."""
    calls: List[str] = []

    class _RaisingInterpreter:
        def __init__(self, app: Any, **kwargs: Any) -> None:
            del app
            calls.append(kwargs["backend"])
            raise BackendUnavailableError(
                "prompt_toolkit backend requested but not installed. Install with: pip install foo"
            )

    monkeypatch.setattr(cli_mod, "ConsoleInterpreter", _RaisingInterpreter)
    monkeypatch.setattr(cli_mod, "run_repl", lambda **_: None)

    result = CliRunner().invoke(cli_mod.repl, ["--backend", "prompt-toolkit"])
    assert result.exit_code != 0
    assert calls == ["prompt-toolkit"]
    assert "prompt_toolkit backend requested but not installed" in result.output


def test_cli_backend_env_var_picked_up(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROBOTCODE_REPL_BACKEND", "readline")
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "readline"


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
    result = CliRunner().invoke(cli_mod.repl, ["--backend", "readline"])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "readline"


def test_cli_repl_backend_env_var_beats_agent_detection(
    capture_interpreter_kwargs: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("ROBOTCODE_REPL_BACKEND", "readline")
    result = CliRunner().invoke(cli_mod.repl, [])
    assert result.exit_code == 0, result.output
    assert capture_interpreter_kwargs["backend"] == "readline"


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
