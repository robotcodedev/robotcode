"""Tests for the AI-agent environment-variable detection."""

import pytest

from robotcode.plugin._agent_detection import (
    _AGENT_ENV_VARS,
    detected_agent_marker,
    is_running_in_ai_agent,
)


@pytest.fixture(autouse=True)
def _scrub_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear every known agent marker plus both override hatches so each
    test starts from a known-empty baseline. Without this the local
    developer's `CLAUDECODE=1` (set when Claude Code runs the suite) would
    contaminate every assertion."""
    for var in (*_AGENT_ENV_VARS, "ROBOTCODE_FORCE_AI_AGENT", "ROBOTCODE_NO_AI_AGENT"):
        monkeypatch.delenv(var, raising=False)


def test_clean_environment_is_not_an_agent() -> None:
    assert is_running_in_ai_agent() is False
    assert detected_agent_marker() == ""


@pytest.mark.parametrize("var", _AGENT_ENV_VARS)
def test_each_known_marker_var_triggers_detection(var: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(var, "1")
    assert is_running_in_ai_agent() is True
    assert detected_agent_marker() == var


@pytest.mark.parametrize("off_value", ["0", "", "   "])
def test_explicit_off_or_blank_marker_does_not_trigger(off_value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """`CLAUDECODE=0`, empty, or whitespace-only counts as "not present"
    — every other value (including ``false`` / ``no`` / agent names /
    session ids) is treated as active, since each agent uses its own
    convention and we'd rather over-detect than fight the agent."""
    monkeypatch.setenv("CLAUDECODE", off_value)
    assert is_running_in_ai_agent() is False
    assert detected_agent_marker() == ""


@pytest.mark.parametrize("value", ["1", "true", "false", "no", "off", "goose", "session-abc123"])
def test_any_non_off_value_is_active(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Agents set markers to varied values — `1`, the agent name, an
    opaque session id, even the literal string `"false"` in odd cases.
    We treat anything that isn't an explicit off-value as active."""
    monkeypatch.setenv("AGENT", value)
    assert is_running_in_ai_agent() is True
    assert detected_agent_marker() == "AGENT"


def test_marker_value_with_whitespace_is_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT", "  goose  ")
    assert is_running_in_ai_agent() is True
    assert detected_agent_marker() == "AGENT"


def test_force_on_wins_with_no_other_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROBOTCODE_FORCE_AI_AGENT", "1")
    assert is_running_in_ai_agent() is True
    assert detected_agent_marker() == "ROBOTCODE_FORCE_AI_AGENT"


def test_force_off_overrides_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("ROBOTCODE_NO_AI_AGENT", "1")
    assert is_running_in_ai_agent() is False
    assert detected_agent_marker() == ""


def test_force_on_beats_force_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """If both override hatches are set, `FORCE_AI_AGENT` wins — the
    user explicitly asked for the agent code path."""
    monkeypatch.setenv("ROBOTCODE_FORCE_AI_AGENT", "1")
    monkeypatch.setenv("ROBOTCODE_NO_AI_AGENT", "1")
    assert is_running_in_ai_agent() is True
    assert detected_agent_marker() == "ROBOTCODE_FORCE_AI_AGENT"


def test_detected_marker_returns_first_in_listed_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """When multiple markers are set, `detected_agent_marker` returns the
    one earliest in `_AGENT_ENV_VARS` — gives diagnostic logs a stable answer."""
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("AGENT", "goose")  # appears earlier in the tuple
    assert detected_agent_marker() == "AGENT"
