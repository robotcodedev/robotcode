"""Tests for the REPL's persistent history infrastructure.

Covers the file-location resolver and the size-cap env-var parser.
Actual history I/O lives inside `PromptToolkitConsoleInterpreter`
and is tested in `test_prompt_toolkit_interpreter.py`.
"""

from pathlib import Path

import pytest

from robotcode.repl._pt.history import (
    DEFAULT_MAX_HISTORY,
    HISTORY_SIZE_ENV_VAR,
    history_path,
    max_history_size,
)


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
