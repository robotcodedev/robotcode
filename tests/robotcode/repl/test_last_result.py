"""Tests for ``${_}`` — Python-REPL-style last-result variable.

`ConsoleInterpreter.set_last_result` runs in Robot's main thread
between keyword executions. We exercise it directly with a stand-in
context, the same trick `test_completion.py` uses to avoid spinning
up a full suite.
"""

from types import SimpleNamespace
from typing import Any, Dict

import pytest
from robot.running.context import EXECUTION_CONTEXTS

from robotcode.repl.console_interpreter import ConsoleInterpreter


def _make_interpreter() -> ConsoleInterpreter:
    """Build a minimal `ConsoleInterpreter` — `app=None` so we don't
    drag in prompt_toolkit / readline. Only the `set_last_result`
    path is exercised here."""
    return ConsoleInterpreter(app=None)


def _patch_context_with_vars(monkeypatch: pytest.MonkeyPatch, store: Dict[str, Any]) -> None:
    """Pretend `EXECUTION_CONTEXTS.current.variables` is a dict — that's
    enough for the `ctx.variables["${_}"] = …` assignment to succeed."""
    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [SimpleNamespace(variables=store)])


def test_set_last_result_publishes_to_robot_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    store: Dict[str, Any] = {}
    _patch_context_with_vars(monkeypatch, store)
    interp = _make_interpreter()

    interp.set_last_result(42)
    assert store["${_}"] == 42


def test_set_last_result_overwrites_on_new_result(monkeypatch: pytest.MonkeyPatch) -> None:
    store: Dict[str, Any] = {}
    _patch_context_with_vars(monkeypatch, store)
    interp = _make_interpreter()

    interp.set_last_result("first")
    interp.set_last_result("second")
    assert store["${_}"] == "second"


def test_set_last_result_none_overwrites(monkeypatch: pytest.MonkeyPatch) -> None:
    """A keyword that returns `None` (e.g. `Log`) resets `${_}` to
    `None`, so `${_}` always mirrors the most recent keyword's result."""
    store: Dict[str, Any] = {}
    _patch_context_with_vars(monkeypatch, store)
    interp = _make_interpreter()

    interp.set_last_result(123)
    interp.set_last_result(None)
    assert store["${_}"] is None


def test_set_last_result_without_context_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    """No active execution context (e.g. teardown phase) → silently skip,
    don't raise."""
    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [])
    interp = _make_interpreter()

    interp.set_last_result("anything")  # must not raise


def test_set_last_result_swallows_scope_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """If Robot's scope rejects the assignment (locked / read-only), the
    REPL keeps running — losing `${_}` for one step beats crashing."""

    class _RaisingVariables:
        def __setitem__(self, key: str, value: Any) -> None:
            raise RuntimeError("scope locked")

    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [SimpleNamespace(variables=_RaisingVariables())])
    interp = _make_interpreter()

    interp.set_last_result(7)  # must not raise


def test_set_last_result_still_updates_base_class_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
    """`BaseInterpreter.last_result` is the canonical Python-side store
    — `${_}` is just a convenience mirror. Both must stay in sync."""
    store: Dict[str, Any] = {}
    _patch_context_with_vars(monkeypatch, store)
    interp = _make_interpreter()

    interp.set_last_result("payload")
    assert interp.last_result == "payload"
    assert store["${_}"] == "payload"
