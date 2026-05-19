"""Tests for the input-backend selection cascade."""

import builtins
import sys
from typing import Any

import pytest

from robotcode.repl._input import PlainBackend, pick_backend
from robotcode.repl._input._plain import PlainBackend as PlainBackendClass


def test_plain_backend_wraps_input(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_input(prompt: str = "") -> str:
        captured["prompt"] = prompt
        return "from-fake-input"

    monkeypatch.setattr(builtins, "input", fake_input)
    backend = PlainBackend()
    result = backend.read_line(">>> ")
    assert result == "from-fake-input"
    assert captured["prompt"] == ">>> "


def test_plain_backend_ignores_prefill(monkeypatch: pytest.MonkeyPatch) -> None:
    """`prefill` is a no-op for PlainBackend (no editor to seed)."""
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "value")
    backend = PlainBackend()
    assert backend.read_line(">>> ", prefill="ignored") == "value"


def test_pick_backend_returns_an_input_backend() -> None:
    """In *any* environment, `pick_backend()` returns a usable backend."""
    backend = pick_backend()
    assert hasattr(backend, "read_line")


def _block_module(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    """Make `import X` raise ImportError for the given module names.

    Setting `sys.modules[name] = None` is the documented Python way of
    deliberately marking a module as unavailable — works regardless of
    whether the import uses absolute or relative syntax.
    """
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)


def test_pick_backend_falls_back_to_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    """When neither prompt_toolkit nor readline can be imported, we get Plain."""
    _block_module(
        monkeypatch,
        "robotcode.repl._input._prompt_toolkit",
        "robotcode.repl._input._readline",
    )
    backend = pick_backend()
    assert isinstance(backend, PlainBackendClass)


def test_pick_backend_picks_readline_when_prompt_toolkit_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Block only prompt_toolkit → readline backend should be selected."""
    pytest.importorskip("readline")  # Unix / Win 3.13+ — skip on bare Windows.

    _block_module(monkeypatch, "robotcode.repl._input._prompt_toolkit")
    backend = pick_backend()
    # We don't import ReadlineBackend at top-level (it may be unavailable),
    # so check by class name to keep the test platform-independent.
    assert type(backend).__name__ == "ReadlineBackend"
