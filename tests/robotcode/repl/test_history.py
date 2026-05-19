"""Tests for the REPL's persistent history infrastructure."""

import atexit
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from robotcode.repl._history import (
    MAX_HISTORY,
    attach_save_on_exit,
    history_path,
    load_into_readline,
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


def _fake_readline(read_history_raises: bool = False) -> ModuleType:
    fake = MagicMock(spec=["set_history_length", "read_history_file", "write_history_file"])
    if read_history_raises:
        fake.read_history_file.side_effect = FileNotFoundError
    return fake


def test_load_into_readline_sets_max_history(tmp_path: Path) -> None:
    fake = _fake_readline()
    target = tmp_path / "hist"
    target.write_text("Log    earlier\n")
    load_into_readline(fake, target)
    fake.set_history_length.assert_called_once_with(MAX_HISTORY)


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
