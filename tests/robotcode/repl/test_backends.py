"""Tests for `cli._pick_interpreter` — picks the interpreter class per `--backend`.

`prompt_toolkit` is a hard runtime dependency of the package, so
`auto` and `prompt-toolkit` always succeed (no install-hint fallback
to verify); only `plain` opts out of the editor surface.
"""

from pathlib import Path
from typing import Any, Optional

import pytest

from robotcode.plugin import Application
from robotcode.repl.cli import _pick_interpreter
from robotcode.repl.console_interpreter import ConsoleInterpreter


def _pick(
    *,
    backend: str,
    files: Any = None,
    no_history: bool = False,
    app: Optional[Application] = None,
) -> ConsoleInterpreter:
    """Test wrapper that supplies the boring defaults — keeps each test
    focused on what's actually relevant (backend + maybe one flag).

    Typed strictly so mypy is satisfied; `**dict` would lose the per-arg
    types because the values have mixed types."""
    return _pick_interpreter(
        app=app,  # type: ignore[arg-type]
        files=files or [],
        show_keywords=False,
        inspect=False,
        no_history=no_history,
        backend=backend,
    )


# ---------------------------------------------------------------------------
# `_pick_interpreter` — backend dispatch
# ---------------------------------------------------------------------------


def test_pick_interpreter_auto_returns_prompt_toolkit() -> None:
    """`auto` picks the prompt-toolkit-driven interpreter."""
    interp = _pick(backend="auto")
    assert type(interp).__name__ == "PromptToolkitConsoleInterpreter"
    assert isinstance(interp, ConsoleInterpreter)


def test_pick_interpreter_explicit_prompt_toolkit_returns_prompt_toolkit() -> None:
    interp = _pick(backend="prompt-toolkit")
    assert type(interp).__name__ == "PromptToolkitConsoleInterpreter"


def test_pick_interpreter_explicit_plain_returns_plain() -> None:
    """`backend="plain"` skips the editor surface — no popup, no ANSI codes
    leaking into AI-agent stdout capture."""
    interp = _pick(backend="plain")
    assert type(interp) is ConsoleInterpreter


def test_pick_interpreter_explicit_plain_is_orthogonal_to_no_history() -> None:
    interp = _pick(backend="plain", no_history=True)
    assert type(interp) is ConsoleInterpreter


def test_pick_interpreter_unknown_value_raises() -> None:
    """Defense in depth: the CLI uses `click.Choice` to filter values,
    but a direct API caller could still pass garbage. Surface it loudly."""
    with pytest.raises(ValueError, match="Unknown backend"):
        _pick(backend="xyz")


# ---------------------------------------------------------------------------
# `ConsoleInterpreter` plain `read_line` — uses stdlib `input()` directly.
# ---------------------------------------------------------------------------


def test_console_interpreter_read_line_wraps_input(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    captured: dict[str, str] = {}

    def fake_input(prompt: str = "") -> str:
        captured["prompt"] = prompt
        return "from-fake-input"

    monkeypatch.setattr(builtins, "input", fake_input)
    interp = ConsoleInterpreter(app=None)
    assert interp.read_line(">>> ") == "from-fake-input"
    assert captured["prompt"] == ">>> "


def test_console_interpreter_read_line_ignores_prefill(monkeypatch: pytest.MonkeyPatch) -> None:
    """`prefill` is a no-op for the plain implementation (no editor to seed)."""
    import builtins

    monkeypatch.setattr(builtins, "input", lambda _prompt="": "value")
    interp = ConsoleInterpreter(app=None)
    assert interp.read_line(">>> ", prefill="ignored") == "value"


def test_console_interpreter_has_no_history_methods() -> None:
    """Plain mode exposes none of the history-management API — the
    `.history` dot-command lives only on the prompt_toolkit subclass."""
    interp = ConsoleInterpreter(app=None)
    assert not hasattr(interp, "get_history")
    assert not hasattr(interp, "clear_history")
    assert not hasattr(interp, "delete_history_entry")


def test_pick_interpreter_passes_files(tmp_path: Path) -> None:
    """`files=` reaches the constructed interpreter for replay."""
    f = tmp_path / "a.robot"
    f.write_text("")
    interp = _pick(backend="plain", files=[f])
    assert interp.files == [f]
