"""Tests for the input-backend selection cascade."""

import builtins
import sys
from typing import Any

import pytest

from robotcode.repl._input import PlainBackend, pick_backend
from robotcode.repl._input._plain import PlainBackend as PlainBackendClass


def _detect_libedit() -> bool:
    """Evaluate at import time whether the active readline is libedit-backed.

    The result drives `pytest.mark.skipif` on history-file tests below: the
    two `readline` implementations write fundamentally different on-disk
    formats (GNU readline: plain lines; libedit / editline: `_HiStOrY_V2_`
    header + escape-encoded entries), so a single fixture file can't satisfy
    both.
    """
    try:
        from robotcode.repl._input._readline import _is_libedit
    except ImportError:
        return False
    return _is_libedit()


_IS_LIBEDIT = _detect_libedit()


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
# Explicit `backend=` selection — forces a specific backend, errors on miss.
# ---------------------------------------------------------------------------


def test_pick_backend_plain_returns_plain_even_with_prompt_toolkit() -> None:
    """`backend="plain"` bypasses the cascade — no popup, no readline,
    no ANSI codes leaking into AI-agent stdout capture."""
    backend = pick_backend(backend="plain")
    assert isinstance(backend, PlainBackendClass)


def test_pick_backend_plain_is_orthogonal_to_no_history() -> None:
    """Plain mode has no history file anyway, but setting both must
    still return PlainBackend (no conflict, no error)."""
    backend = pick_backend(backend="plain", no_history=True)
    assert isinstance(backend, PlainBackendClass)


def test_pick_backend_auto_keeps_default_cascade(monkeypatch: pytest.MonkeyPatch) -> None:
    """`backend="auto"` (the default) must NOT short-circuit; cascade as
    before."""
    pytest.importorskip("readline")
    _block_module(monkeypatch, "robotcode.repl._input._prompt_toolkit")
    backend = pick_backend(backend="auto")
    assert type(backend).__name__ == "ReadlineBackend"


def test_pick_backend_explicit_readline_returns_readline_even_with_prompt_toolkit() -> None:
    """Core feature: `backend="readline"` must ignore prompt_toolkit
    even when it's installed. Lets devs (and users) exercise the
    readline code path without uninstalling the prompt_toolkit extra."""
    pytest.importorskip("readline")
    pytest.importorskip("prompt_toolkit")
    backend = pick_backend(backend="readline")
    assert type(backend).__name__ == "ReadlineBackend"


def test_pick_backend_explicit_prompt_toolkit_returns_prompt_toolkit() -> None:
    pytest.importorskip("prompt_toolkit")
    backend = pick_backend(backend="prompt-toolkit")
    assert type(backend).__name__ == "PromptToolkitBackend"


def test_pick_backend_explicit_readline_raises_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit request for an uninstalled backend is a hard error —
    silent fallback would defeat the purpose of the flag."""
    from robotcode.repl._input import BackendUnavailableError

    _block_module(monkeypatch, "robotcode.repl._input._readline")
    with pytest.raises(BackendUnavailableError, match="readline backend not available"):
        pick_backend(backend="readline")


def test_pick_backend_explicit_prompt_toolkit_raises_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from robotcode.repl._input import BackendUnavailableError

    _block_module(monkeypatch, "robotcode.repl._input._prompt_toolkit")
    with pytest.raises(BackendUnavailableError, match="prompt_toolkit backend requested"):
        pick_backend(backend="prompt-toolkit")


def test_pick_backend_unknown_value_raises() -> None:
    """Defense in depth: the CLI uses `click.Choice` to filter values,
    but a direct API caller could still pass garbage. Surface it loudly."""
    with pytest.raises(ValueError, match="Unknown backend"):
        pick_backend(backend="xyz")


# ---------------------------------------------------------------------------
# History-protocol methods (InputBackend.get_history / clear / delete)
# ---------------------------------------------------------------------------


def test_plain_backend_history_methods_are_no_ops() -> None:
    backend = PlainBackend()
    assert backend.get_history() == []
    backend.clear_history()  # must not raise
    assert backend.delete_history_entry(1) is False


def _seed_history_via_readline(monkeypatch: pytest.MonkeyPatch, tmp_path: Any, lines: list[str]) -> Any:
    """Populate `tmp_path/histfile` using `readline.write_history_file`.

    The on-disk format matches whichever backend (GNU readline or libedit)
    is in use — libedit adds the `_HiStOrY_V2_` marker it later expects when
    reading back, GNU readline writes plain lines. Tests that go through
    this seed step therefore behave the same way under both backends.
    """
    histfile = tmp_path / "histfile"

    import robotcode.repl._history as history_mod

    monkeypatch.setattr(history_mod, "history_path", lambda: histfile)

    from robotcode.repl._input import _readline as readline_mod

    _rl = readline_mod.readline  # type: ignore[attr-defined]
    _rl.clear_history()
    for line in lines:
        _rl.add_history(line)
    _rl.write_history_file(str(histfile))
    _rl.clear_history()
    return histfile


@pytest.mark.skipif(
    _IS_LIBEDIT,
    reason="plain-text fixture only loads on GNU readline; libedit variant below",
)
def test_readline_backend_history_round_trip_gnu_format(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """GNU readline reads a hand-written plain-text history file as-is.

    `delete_history_line_in_file` and `truncate_history_file` operate on
    the file as plain text, so the on-disk content here is asserted
    directly. The libedit equivalent (next test) goes through readline's
    own writer for seeding because the libedit format isn't plain text.
    """
    pytest.importorskip("readline")
    histfile = tmp_path / "histfile"
    histfile.write_text("first\nsecond\nthird\n")

    import robotcode.repl._history as history_mod

    monkeypatch.setattr(history_mod, "history_path", lambda: histfile)

    from robotcode.repl._input import _readline as readline_mod
    from robotcode.repl._input._readline import ReadlineBackend

    _rl = readline_mod.readline  # type: ignore[attr-defined]

    _rl.clear_history()
    backend = ReadlineBackend()
    assert backend.get_history() == ["first", "second", "third"]

    assert backend.delete_history_entry(2) is True
    assert backend.get_history() == ["first", "third"]
    assert "second" not in histfile.read_text()

    backend.clear_history()
    assert backend.get_history() == []
    assert histfile.read_text() == ""


@pytest.mark.skipif(not _IS_LIBEDIT, reason="libedit-specific round-trip; the GNU variant runs above")
def test_readline_backend_history_round_trip_libedit_format(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """libedit equivalent of the GNU round-trip: seed via readline's own
    `write_history_file` so the file gets libedit's expected header.

    `delete_history_line_in_file` is text-line-based and gets out of sync
    with the in-memory ring by one (the header) on libedit, so file-content
    invariants from the GNU test are deliberately not asserted here —
    only the in-memory ring is the authoritative store on libedit.
    """
    pytest.importorskip("readline")
    histfile = _seed_history_via_readline(monkeypatch, tmp_path, ["first", "second", "third"])

    from robotcode.repl._input._readline import ReadlineBackend

    backend = ReadlineBackend()
    assert backend.get_history() == ["first", "second", "third"]

    assert backend.delete_history_entry(2) is True
    assert backend.get_history() == ["first", "third"]

    backend.clear_history()
    assert backend.get_history() == []
    assert histfile.read_text() == ""


def test_readline_backend_delete_out_of_range(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Out-of-range index returns False and leaves history intact, on
    either backend (seeded via the readline-native writer so both formats work)."""
    pytest.importorskip("readline")
    _seed_history_via_readline(monkeypatch, tmp_path, ["only"])

    from robotcode.repl._input._readline import ReadlineBackend

    backend = ReadlineBackend()
    assert backend.delete_history_entry(99) is False
    assert backend.delete_history_entry(0) is False
    assert backend.get_history() == ["only"]
