"""Tests for the input-backend selection cascade."""

import builtins
import sys
from typing import Any

import pytest

from robotcode.repl._input import BackendUnavailableError, PlainBackend, pick_backend

# ---------------------------------------------------------------------------
# PlainBackend
# ---------------------------------------------------------------------------


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


def test_plain_backend_has_no_history_capability() -> None:
    """PlainBackend exposes only `read_line` — the `.history` dot-command
    detects that and tells the user to install the prompt_toolkit extra."""
    backend = PlainBackend()
    assert not hasattr(backend, "get_history")
    assert not hasattr(backend, "clear_history")
    assert not hasattr(backend, "delete_history_entry")


# ---------------------------------------------------------------------------
# pick_backend — the 2-tier cascade
# ---------------------------------------------------------------------------


def _block_module(monkeypatch: pytest.MonkeyPatch, *names: str) -> None:
    """Make `import X` raise ImportError for the given module names."""
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)


def test_pick_backend_returns_an_input_backend() -> None:
    """In *any* environment, `pick_backend()` returns something with `read_line`."""
    backend = pick_backend()
    assert hasattr(backend, "read_line")


def test_pick_backend_prefers_prompt_toolkit_when_available() -> None:
    pytest.importorskip("prompt_toolkit")
    backend = pick_backend()
    assert type(backend).__name__ == "PromptToolkitBackend"


def test_pick_backend_falls_back_to_plain_when_prompt_toolkit_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blocking the prompt_toolkit import drops `auto` to plain."""
    _block_module(monkeypatch, "robotcode.repl._input._prompt_toolkit")
    backend = pick_backend()
    assert isinstance(backend, PlainBackend)


# ---------------------------------------------------------------------------
# Explicit `backend=` selection
# ---------------------------------------------------------------------------


def test_pick_backend_explicit_plain_returns_plain_even_with_prompt_toolkit() -> None:
    """`backend="plain"` bypasses the cascade — no popup, no ANSI codes
    leaking into AI-agent stdout capture."""
    backend = pick_backend(backend="plain")
    assert isinstance(backend, PlainBackend)


def test_pick_backend_explicit_plain_is_orthogonal_to_no_history() -> None:
    backend = pick_backend(backend="plain", no_history=True)
    assert isinstance(backend, PlainBackend)


def test_pick_backend_explicit_prompt_toolkit_returns_prompt_toolkit() -> None:
    pytest.importorskip("prompt_toolkit")
    backend = pick_backend(backend="prompt-toolkit")
    assert type(backend).__name__ == "PromptToolkitBackend"


def test_pick_backend_explicit_prompt_toolkit_raises_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit request for the missing extra is a hard error — silent
    fallback would defeat the purpose of the flag."""
    _block_module(monkeypatch, "robotcode.repl._input._prompt_toolkit")
    with pytest.raises(BackendUnavailableError, match="prompt_toolkit backend requested"):
        pick_backend(backend="prompt-toolkit")


def test_pick_backend_unknown_value_raises() -> None:
    """Defense in depth: the CLI uses `click.Choice` to filter values,
    but a direct API caller could still pass garbage. Surface it loudly."""
    with pytest.raises(ValueError, match="Unknown backend"):
        pick_backend(backend="xyz")
