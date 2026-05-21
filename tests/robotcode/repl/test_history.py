"""Tests for the REPL's persistent history infrastructure."""

import atexit
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, List, Optional
from unittest.mock import MagicMock

import pytest

from robotcode.repl._history import (
    DEFAULT_MAX_HISTORY,
    HISTORY_SIZE_ENV_VAR,
    attach_save_on_exit,
    dedup_last_entry,
    history_path,
    load_into_readline,
    max_history_size,
)

# ---------------------------------------------------------------------------
# history_path() — project-aware + env override
# ---------------------------------------------------------------------------


def test_history_path_returns_absolute_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Without `ROBOTCODE_CACHE_DIR`, `history_path()` returns an absolute file path."""
    monkeypatch.delenv("ROBOTCODE_CACHE_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    p = history_path()
    assert p.is_absolute()
    assert p.name == "repl_history"


def test_history_path_uses_project_cache_when_in_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """In a directory with `robot.toml`, history lands in `.robotcode_cache/`."""
    monkeypatch.delenv("ROBOTCODE_CACHE_DIR", raising=False)
    (tmp_path / "robot.toml").write_text("")
    monkeypatch.chdir(tmp_path)
    p = history_path()
    # Resolve both paths to handle macOS's /tmp → /private/tmp symlink.
    assert p == (tmp_path / ".robotcode_cache" / "repl_history").resolve()


def test_history_path_uses_user_cache_outside_project(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Outside any project, the file lands in the user cache directory."""
    monkeypatch.delenv("ROBOTCODE_CACHE_DIR", raising=False)
    # tmp_path has no robot.toml / pyproject.toml / .git → not a project.
    monkeypatch.chdir(tmp_path)
    p = history_path()
    # Path should NOT be inside tmp_path — should be the per-user cache.
    assert not str(p).startswith(str(tmp_path))


def test_history_path_env_override_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`ROBOTCODE_CACHE_DIR` overrides both project and user-cache."""
    override = tmp_path / "custom-cache"
    monkeypatch.setenv("ROBOTCODE_CACHE_DIR", str(override))
    (tmp_path / "robot.toml").write_text("")  # project marker — should be ignored
    monkeypatch.chdir(tmp_path)
    p = history_path()
    assert p == override / "repl_history"


# ---------------------------------------------------------------------------
# load_into_readline() — sets length, reads file if present
# ---------------------------------------------------------------------------


def _fake_readline(read_history_raises: bool = False, initial: Optional[List[str]] = None) -> ModuleType:
    """Build a `readline`-like Mock with a working in-memory history.

    `initial` seeds the history buffer (1-based indexing per readline's
    API). All four mutation methods we exercise — `set_history_length`,
    `read_history_file`, `write_history_file`, `get_history_item`,
    `remove_history_item`, `get_current_history_length` — are wired so
    tests can inspect both call-record and state.
    """
    fake = MagicMock(
        spec=[
            "set_history_length",
            "read_history_file",
            "write_history_file",
            "get_current_history_length",
            "get_history_item",
            "remove_history_item",
        ]
    )
    state: List[str] = list(initial or [])
    fake.get_current_history_length.side_effect = lambda: len(state)
    # readline's get_history_item is 1-based; returns None for out-of-range.
    fake.get_history_item.side_effect = lambda i: state[i - 1] if 1 <= i <= len(state) else None
    # remove_history_item is 0-based.
    fake.remove_history_item.side_effect = lambda i: state.pop(i)
    fake._state = state
    if read_history_raises:
        fake.read_history_file.side_effect = FileNotFoundError
    return fake


def test_load_into_readline_sets_max_history(tmp_path: Path) -> None:
    fake = _fake_readline()
    target = tmp_path / "hist"
    target.write_text("Log    earlier\n")
    load_into_readline(fake, target)
    fake.set_history_length.assert_called_once_with(DEFAULT_MAX_HISTORY)


def test_load_into_readline_reads_existing_file(tmp_path: Path) -> None:
    fake = _fake_readline()
    target = tmp_path / "hist"
    target.write_text("Log    earlier\n")
    load_into_readline(fake, target)
    fake.read_history_file.assert_called_once_with(str(target))


def test_load_into_readline_tolerates_missing_file(tmp_path: Path) -> None:
    """No prior history → no exception, just an empty buffer."""
    fake = _fake_readline(read_history_raises=True)
    target = tmp_path / "does-not-exist"
    load_into_readline(fake, target)  # must not raise
    fake.read_history_file.assert_called_once_with(str(target))


def test_load_into_readline_dedupes_legacy_file(tmp_path: Path) -> None:
    """A history file from a pre-dedup version (with duplicates) gets cleaned
    up on load — the newest occurrence of each line survives, older copies
    are dropped."""
    target = tmp_path / "hist"
    target.write_text("placeholder\n")  # presence triggers read_history_file
    fake = _fake_readline(initial=["Log    a", "Log    b", "Log    a", "Log    c", "Log    b"])
    load_into_readline(fake, target)
    # Expected survivors (newest occurrence per unique line, in order):
    #   Log    a (idx 3 was newer than idx 1 → idx 1 dropped)
    #   Log    c (idx 4 unique)
    #   Log    b (idx 5 was newer than idx 2 → idx 2 dropped)
    # Result after dedup: ['Log    a', 'Log    c', 'Log    b']
    assert fake._state == ["Log    a", "Log    c", "Log    b"]


# ---------------------------------------------------------------------------
# max_history_size() — env-var configurable, sane defaults
# ---------------------------------------------------------------------------


def test_max_history_size_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(HISTORY_SIZE_ENV_VAR, raising=False)
    assert max_history_size() == DEFAULT_MAX_HISTORY


def test_max_history_size_honours_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HISTORY_SIZE_ENV_VAR, "250")
    assert max_history_size() == 250


@pytest.mark.parametrize("bad_value", ["", "foo", "0", "-5", "1.5"])
def test_max_history_size_falls_back_on_bad_input(monkeypatch: pytest.MonkeyPatch, bad_value: str) -> None:
    """Empty / non-numeric / non-positive values never raise — just default."""
    monkeypatch.setenv(HISTORY_SIZE_ENV_VAR, bad_value)
    assert max_history_size() == DEFAULT_MAX_HISTORY


def test_load_into_readline_uses_configured_size(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(HISTORY_SIZE_ENV_VAR, "42")
    fake = _fake_readline(read_history_raises=True)
    load_into_readline(fake, tmp_path / "hist")
    fake.set_history_length.assert_called_once_with(42)


# ---------------------------------------------------------------------------
# dedup_last_entry() — fish-style: older copies drop, newest stays
# ---------------------------------------------------------------------------


def test_dedup_last_entry_removes_older_duplicates() -> None:
    fake = _fake_readline(initial=["Log    a", "Log    b", "Log    a"])
    dedup_last_entry(fake)
    # Newest 'Log    a' stays, the older one (index 1) is gone.
    assert fake._state == ["Log    b", "Log    a"]


def test_dedup_last_entry_noop_when_unique() -> None:
    fake = _fake_readline(initial=["Log    a", "Log    b", "Log    c"])
    dedup_last_entry(fake)
    assert fake._state == ["Log    a", "Log    b", "Log    c"]


def test_dedup_last_entry_handles_empty_history() -> None:
    fake = _fake_readline(initial=[])
    dedup_last_entry(fake)  # must not raise
    assert fake._state == []


def test_dedup_last_entry_keeps_only_latest_among_many_duplicates() -> None:
    fake = _fake_readline(initial=["x", "Log    a", "y", "Log    a", "z", "Log    a"])
    dedup_last_entry(fake)
    # Only the trailing 'Log    a' (the latest) survives.
    assert fake._state == ["x", "y", "z", "Log    a"]


def test_dedup_last_entry_ignores_blank_latest() -> None:
    """A blank line at the top of the buffer never triggers dedup."""
    fake = _fake_readline(initial=["Log    a", "Log    a", ""])
    dedup_last_entry(fake)
    # The blank entry doesn't match-and-purge the duplicates above it.
    assert fake._state == ["Log    a", "Log    a", ""]


# ---------------------------------------------------------------------------
# pyreadline3 fallback — clear + re-add when remove_history_item is missing
# ---------------------------------------------------------------------------


def _fake_readline_without_remove(initial: Optional[List[str]] = None) -> ModuleType:
    """Mimics pyreadline3 on Windows: every history method is there *except*
    `remove_history_item`. Uses `clear_history` + `add_history` instead."""
    fake = MagicMock(
        spec=[
            "set_history_length",
            "read_history_file",
            "write_history_file",
            "get_current_history_length",
            "get_history_item",
            "clear_history",
            "add_history",
        ]
    )
    state: List[str] = list(initial or [])
    fake.get_current_history_length.side_effect = lambda: len(state)
    fake.get_history_item.side_effect = lambda i: state[i - 1] if 1 <= i <= len(state) else None
    fake.clear_history.side_effect = lambda: state.clear()
    fake.add_history.side_effect = lambda line: state.append(line)
    fake._state = state
    return fake


def test_dedup_last_entry_uses_clear_add_fallback_when_remove_missing() -> None:
    """The pyreadline3 path: `remove_history_item` is absent, so the dedup
    rebuilds the buffer via `clear_history` + `add_history`. This is the
    regression test for the Windows startup crash."""
    fake = _fake_readline_without_remove(initial=["Log    a", "Log    b", "Log    a"])
    dedup_last_entry(fake)
    assert fake._state == ["Log    b", "Log    a"]
    fake.clear_history.assert_called_once()


def test_load_into_readline_dedupes_via_fallback_when_remove_missing(tmp_path: Path) -> None:
    target = tmp_path / "hist"
    target.write_text("placeholder\n")
    fake = _fake_readline_without_remove(initial=["Log    a", "Log    b", "Log    a", "Log    c", "Log    b"])
    load_into_readline(fake, target)
    assert fake._state == ["Log    a", "Log    c", "Log    b"]
    fake.clear_history.assert_called_once()


# ---------------------------------------------------------------------------
# attach_save_on_exit() — TTY-gated, writes via atexit
# ---------------------------------------------------------------------------


def _capture_atexit_hooks(monkeypatch: pytest.MonkeyPatch) -> List[Any]:
    """Replace `atexit.register` with a list collector so tests can inspect."""
    hooks: List[Any] = []

    def _register(fn: Any, *_args: Any, **_kwargs: Any) -> Any:
        hooks.append(fn)
        return fn

    monkeypatch.setattr(atexit, "register", _register)
    return hooks


def test_attach_save_on_exit_skips_when_stdin_not_tty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Piped stdin (CI, scripts) → no atexit handler registered."""
    hooks = _capture_atexit_hooks(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    attach_save_on_exit(_fake_readline(), tmp_path / "hist")
    assert hooks == []


def test_attach_save_on_exit_writes_on_tty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """TTY stdin → registers a hook that writes the history file."""
    hooks = _capture_atexit_hooks(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    fake = _fake_readline()
    target = tmp_path / "subdir" / "hist"  # parent dir must be created on save
    attach_save_on_exit(fake, target)
    assert len(hooks) == 1
    # Invoke the hook to simulate process shutdown.
    hooks[0]()
    fake.write_history_file.assert_called_once_with(str(target))
    assert target.parent.is_dir(), "save hook must mkdir -p"


def test_attach_save_on_exit_swallows_oserror(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Disk-full / permission errors on shutdown must not crash the REPL."""
    hooks = _capture_atexit_hooks(monkeypatch)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    fake = _fake_readline()
    fake.write_history_file.side_effect = OSError("disk full")
    attach_save_on_exit(fake, tmp_path / "hist")
    # Hook execution must not propagate the OSError.
    hooks[0]()


# ---------------------------------------------------------------------------
# Cross-test cleanup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent stray ROBOTCODE_CACHE_DIR from a parent shell leaking in."""
    if "ROBOTCODE_CACHE_DIR" in os.environ:
        monkeypatch.delenv("ROBOTCODE_CACHE_DIR")
