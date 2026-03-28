"""Tests for SqliteDataCache backend."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from robotcode.robot.diagnostics.data_cache import CacheSection, SqliteDataCache


@dataclass
class _SampleData:
    name: str
    value: int


class TestSqliteDataCache:
    def test_save_and_read_roundtrip(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        data = _SampleData(name="hello", value=42)

        cache.save_cache_data(CacheSection.LIBRARY, "entry1", data)
        result = cache.read_cache_data(CacheSection.LIBRARY, "entry1", _SampleData)

        assert result == data

    def test_cache_data_exists_true(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_cache_data(CacheSection.LIBRARY, "exists", "some data")

        assert cache.cache_data_exists(CacheSection.LIBRARY, "exists") is True

    def test_cache_data_exists_false(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")

        assert cache.cache_data_exists(CacheSection.LIBRARY, "missing") is False

    def test_read_missing_entry_raises_file_not_found(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")

        with pytest.raises(FileNotFoundError):
            cache.read_cache_data(CacheSection.LIBRARY, "missing", str)

    def test_read_wrong_type_raises_type_error(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_cache_data(CacheSection.LIBRARY, "entry", "a string")

        with pytest.raises(TypeError):
            cache.read_cache_data(CacheSection.LIBRARY, "entry", int)

    def test_overwrite_existing_entry(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_cache_data(CacheSection.LIBRARY, "entry", "first")
        cache.save_cache_data(CacheSection.LIBRARY, "entry", "second")

        result = cache.read_cache_data(CacheSection.LIBRARY, "entry", str)
        assert result == "second"

    def test_different_sections_independent(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_cache_data(CacheSection.LIBRARY, "entry", "lib_data")
        cache.save_cache_data(CacheSection.RESOURCE, "entry", "res_data")

        assert cache.read_cache_data(CacheSection.LIBRARY, "entry", str) == "lib_data"
        assert cache.read_cache_data(CacheSection.RESOURCE, "entry", str) == "res_data"

    def test_different_entry_names_independent(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_cache_data(CacheSection.LIBRARY, "a", 1)
        cache.save_cache_data(CacheSection.LIBRARY, "b", 2)

        assert cache.read_cache_data(CacheSection.LIBRARY, "a", int) == 1
        assert cache.read_cache_data(CacheSection.LIBRARY, "b", int) == 2

    def test_data_persists_after_close_and_reopen(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)
        cache.save_cache_data(CacheSection.NAMESPACE, "entry", {"key": "value"})
        cache.close()

        cache2 = SqliteDataCache(cache_dir)
        result = cache2.read_cache_data(CacheSection.NAMESPACE, "entry", dict)
        assert result == {"key": "value"}
        cache2.close()

    def test_creates_cache_dir_and_gitignore(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "new_cache"
        assert not cache_dir.exists()

        SqliteDataCache(cache_dir)

        assert cache_dir.exists()
        gitignore = cache_dir / ".gitignore"
        assert gitignore.exists()
        assert "*" in gitignore.read_text("utf-8")

    def test_creates_db_file(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        SqliteDataCache(cache_dir)

        assert (cache_dir / "cache.db").exists()

    def test_complex_data_roundtrip(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        data = {
            "strings": ["a", "b", "c"],
            "nested": {"x": 1, "y": [2, 3]},
            "none_val": None,
            "tuple_as_list": [1, 2, 3],
        }

        cache.save_cache_data(CacheSection.VARIABLES, "complex", data)
        result = cache.read_cache_data(CacheSection.VARIABLES, "complex", dict)
        assert result == data
