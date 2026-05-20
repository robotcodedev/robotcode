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


def test_pick_backend_threads_no_history_to_readline(monkeypatch: pytest.MonkeyPatch) -> None:
    """`pick_backend(no_history=True)` must skip the history file calls in
    the readline backend — verified by patching the load/save helpers."""
    pytest.importorskip("readline")
    _block_module(monkeypatch, "robotcode.repl._input._prompt_toolkit")

    from robotcode.repl._input import _readline as readline_backend_mod

    load_calls: list[Any] = []
    save_calls: list[Any] = []
    monkeypatch.setattr(readline_backend_mod, "load_into_readline", lambda *a, **kw: load_calls.append(a))
    monkeypatch.setattr(readline_backend_mod, "attach_save_on_exit", lambda *a, **kw: save_calls.append(a))

    backend = pick_backend(no_history=True)
    assert type(backend).__name__ == "ReadlineBackend"
    assert load_calls == [], "no_history must skip load_into_readline"
    assert save_calls == [], "no_history must skip attach_save_on_exit"


def test_pick_backend_default_loads_and_saves_readline_history(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default `pick_backend()` keeps the readline backend's load+save behaviour."""
    pytest.importorskip("readline")
    _block_module(monkeypatch, "robotcode.repl._input._prompt_toolkit")

    from robotcode.repl._input import _readline as readline_backend_mod

    load_calls: list[Any] = []
    save_calls: list[Any] = []
    monkeypatch.setattr(readline_backend_mod, "load_into_readline", lambda *a, **kw: load_calls.append(a))
    monkeypatch.setattr(readline_backend_mod, "attach_save_on_exit", lambda *a, **kw: save_calls.append(a))

    pick_backend()
    assert load_calls, "default must call load_into_readline"
    assert save_calls, "default must call attach_save_on_exit"


# ---------------------------------------------------------------------------
# prompt_toolkit backend — only runs when the optional extra is installed.
# ---------------------------------------------------------------------------


def test_pick_backend_prefers_prompt_toolkit_when_available() -> None:
    """When `prompt_toolkit` is importable, `pick_backend()` returns it."""
    pytest.importorskip("prompt_toolkit")
    backend = pick_backend()
    assert type(backend).__name__ == "PromptToolkitBackend"


# ---------------------------------------------------------------------------
# --plain escape hatch — forces PlainBackend regardless of installed extras.
# ---------------------------------------------------------------------------


def test_pick_backend_plain_returns_plain_even_with_prompt_toolkit() -> None:
    """`plain=True` must bypass the cascade — no popup, no readline, no
    ANSI codes leaking into AI-agent stdout capture."""
    backend = pick_backend(plain=True)
    assert isinstance(backend, PlainBackendClass)


def test_pick_backend_plain_is_orthogonal_to_no_history() -> None:
    """Plain mode has no history file anyway, but setting both must
    still return PlainBackend (no conflict, no error)."""
    backend = pick_backend(plain=True, no_history=True)
    assert isinstance(backend, PlainBackendClass)


def test_pick_backend_plain_false_keeps_default_cascade(monkeypatch: pytest.MonkeyPatch) -> None:
    """`plain=False` (the default) must NOT short-circuit; cascade as
    before."""
    pytest.importorskip("readline")
    _block_module(monkeypatch, "robotcode.repl._input._prompt_toolkit")
    backend = pick_backend(plain=False)
    assert type(backend).__name__ == "ReadlineBackend"
