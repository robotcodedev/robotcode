from pathlib import Path

import pytest

from robotcode.analyze.cache.cli import _display_name, _entry_matches, _resolve_cache, _resolve_cache_root
from robotcode.plugin import Application
from robotcode.robot.diagnostics.data_cache import CACHE_DIR_NAME, build_cache_dir


class TestEntryMatches:
    def test_no_patterns_matches_everything(self) -> None:
        assert _entry_matches("/project/suite.robot\nrobot", ()) is True

    def test_plain_entry_matches_by_glob(self) -> None:
        assert _entry_matches("/project/common.resource", ("*.resource",)) is True
        assert _entry_matches("/project/common.resource", ("*.robot",)) is False

    def test_namespace_entry_matches_by_source_glob(self) -> None:
        # namespace entry names carry a "\n<document type>" suffix; a path
        # glob must still match them
        assert _entry_matches("/project/suite.robot\nrobot", ("*/suite.robot",)) is True
        assert _entry_matches("/project/common.resource\nresource", ("*.resource",)) is True

    def test_namespace_entry_matches_by_full_name(self) -> None:
        assert _entry_matches("/project/suite.robot\nrobot", ("*suite.robot*",)) is True

    def test_non_matching_pattern(self) -> None:
        assert _entry_matches("/project/suite.robot\nrobot", ("*/other.robot",)) is False


def test_display_name_keeps_entry_single_line() -> None:
    assert _display_name("/project/suite.robot\nrobot") == "/project/suite.robot · robot"
    assert _display_name("/project/common.resource") == "/project/common.resource"


def _project_with_cache_dir(tmp_path: Path) -> Application:
    (tmp_path / "robot.toml").write_text('[tool.robotcode-analyze.cache]\ncache-dir = "mycache"\n', encoding="utf-8")
    (tmp_path / "tests").mkdir()
    app = Application()
    app.config.root = tmp_path
    return app


def test_cache_dir_counts_from_the_project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ROBOTCODE_CACHE_DIR", raising=False)
    app = _project_with_cache_dir(tmp_path)
    monkeypatch.chdir(tmp_path / "tests")

    cache_dir, _db = _resolve_cache(app, ())

    assert cache_dir.resolve() == build_cache_dir(tmp_path / "mycache").resolve()
    assert _resolve_cache_root(app, ()).resolve() == (tmp_path / "mycache" / CACHE_DIR_NAME).resolve()


def test_robotcode_cache_dir_wins_over_cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROBOTCODE_CACHE_DIR", str(tmp_path / "env"))
    app = _project_with_cache_dir(tmp_path)

    cache_dir, _db = _resolve_cache(app, ())

    assert cache_dir.resolve() == build_cache_dir(tmp_path / "env").resolve()
