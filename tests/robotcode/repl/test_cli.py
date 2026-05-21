"""Click-level tests for `robotcode repl` flags.

Focused on flag parsing and translation — the interpreter itself is
mocked out so the test never starts a real prompt session.
"""

from typing import Any, Dict, List

import pytest
from click.testing import CliRunner

from robotcode.repl import cli as cli_mod
from robotcode.repl._input import BackendUnavailableError


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
