"""Tests for SqliteDataCache backend."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytest

from robotcode.robot.diagnostics.data_cache import CacheEntry, CacheSection, SqliteDataCache


@dataclass
class _SampleMeta:
    name: str
    version: int


@dataclass
class _SampleData:
    name: str
    value: int


class TestCacheEntry:
    def _make_entry(
        self,
        meta_blob: "Optional[bytes]",
        data_blob: bytes,
        meta_type: type,
        data_type: type,
    ) -> CacheEntry:  # type: ignore[type-arg]
        """Create a CacheEntry backed by a temporary in-memory DB."""
        import sqlite3

        conn = sqlite3.connect(":memory:")
        table = CacheSection.LIBRARY.value
        conn.execute(f"CREATE TABLE {table} (entry_name TEXT PRIMARY KEY, meta BLOB, data BLOB NOT NULL)")
        conn.execute(
            f"INSERT INTO {table} (entry_name, meta, data) VALUES (?, ?, ?)",
            ("test_entry", meta_blob, data_blob),
        )
        return CacheEntry(conn, CacheSection.LIBRARY, "test_entry", meta_blob, meta_type, data_type)

    def test_lazy_meta_deserialization(self) -> None:
        import pickle

        meta = _SampleMeta(name="test", version=1)
        data = _SampleData(name="hello", value=42)
        entry = self._make_entry(
            pickle.dumps(meta),
            pickle.dumps(data),
            _SampleMeta,
            _SampleData,
        )
        assert entry.meta == meta
        # Second access returns cached value
        assert entry.meta == meta

    def test_lazy_data_deserialization(self) -> None:
        import pickle

        data = _SampleData(name="hello", value=42)
        entry = self._make_entry(
            None,
            pickle.dumps(data),
            _SampleMeta,
            _SampleData,
        )
        assert entry.meta is None
        assert entry.data == data

    def test_meta_type_mismatch_raises(self) -> None:
        import pickle

        entry = self._make_entry(
            pickle.dumps("not a meta"),
            pickle.dumps("data"),
            _SampleMeta,
            str,
        )
        with pytest.raises(TypeError):
            _ = entry.meta

    def test_data_type_mismatch_raises(self) -> None:
        import pickle

        entry = self._make_entry(
            None,
            pickle.dumps("not data"),
            _SampleMeta,
            _SampleData,
        )
        with pytest.raises(TypeError):
            _ = entry.data


class TestSqliteDataCache:
    def test_save_and_read_roundtrip(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        meta = _SampleMeta(name="hello", version=1)
        data = _SampleData(name="hello", value=42)

        cache.save_entry(CacheSection.LIBRARY, "entry1", meta, data)
        entry = cache.read_entry(CacheSection.LIBRARY, "entry1", _SampleMeta, _SampleData)

        assert entry is not None
        assert entry.meta == meta
        assert entry.data == data

    def test_read_missing_entry_returns_none(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")

        assert cache.read_entry(CacheSection.LIBRARY, "missing", _SampleMeta, _SampleData) is None

    def test_overwrite_existing_entry(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        meta1 = _SampleMeta(name="first", version=1)
        data1 = _SampleData(name="first", value=1)
        meta2 = _SampleMeta(name="second", version=2)
        data2 = _SampleData(name="second", value=2)
        cache.save_entry(CacheSection.LIBRARY, "entry", meta1, data1)
        cache.save_entry(CacheSection.LIBRARY, "entry", meta2, data2)

        entry = cache.read_entry(CacheSection.LIBRARY, "entry", _SampleMeta, _SampleData)
        assert entry is not None
        assert entry.meta == _SampleMeta(name="second", version=2)
        assert entry.data == _SampleData(name="second", value=2)

    def test_different_sections_independent(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_entry(CacheSection.LIBRARY, "entry", None, "lib_data")
        cache.save_entry(CacheSection.RESOURCE, "entry", None, "res_data")

        lib_entry = cache.read_entry(CacheSection.LIBRARY, "entry", str, str)
        res_entry = cache.read_entry(CacheSection.RESOURCE, "entry", str, str)
        assert lib_entry is not None
        assert lib_entry.data == "lib_data"
        assert res_entry is not None
        assert res_entry.data == "res_data"

    def test_different_entry_names_independent(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_entry(CacheSection.LIBRARY, "a", None, 1)
        cache.save_entry(CacheSection.LIBRARY, "b", None, 2)

        entry_a = cache.read_entry(CacheSection.LIBRARY, "a", str, int)
        entry_b = cache.read_entry(CacheSection.LIBRARY, "b", str, int)
        assert entry_a is not None
        assert entry_a.data == 1
        assert entry_b is not None
        assert entry_b.data == 2

    def test_data_persists_after_close_and_reopen(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)
        cache.save_entry(CacheSection.NAMESPACE, "entry", "meta_val", {"key": "value"})
        cache.close()

        cache2 = SqliteDataCache(cache_dir)
        entry = cache2.read_entry(CacheSection.NAMESPACE, "entry", str, dict)
        assert entry is not None
        assert entry.data == {"key": "value"}
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

        cache.save_entry(CacheSection.VARIABLES, "complex", None, data)
        entry = cache.read_entry(CacheSection.VARIABLES, "complex", str, dict)
        assert entry is not None
        assert entry.data == data

    def test_app_version_mismatch_clears_data(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir, app_version="1.0.0")
        cache.save_entry(CacheSection.LIBRARY, "entry", None, "old_data")
        cache.close()

        cache2 = SqliteDataCache(cache_dir, app_version="2.0.0")
        entry = cache2.read_entry(CacheSection.LIBRARY, "entry", str, str)
        assert entry is None
        cache2.close()

    def test_app_version_match_preserves_data(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir, app_version="1.0.0")
        cache.save_entry(CacheSection.LIBRARY, "entry", None, "data")
        cache.close()

        cache2 = SqliteDataCache(cache_dir, app_version="1.0.0")
        entry = cache2.read_entry(CacheSection.LIBRARY, "entry", str, str)
        assert entry is not None
        assert entry.data == "data"
        cache2.close()

    def test_save_entry_with_none_meta(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_entry(CacheSection.LIBRARY, "entry", None, "data")

        entry = cache.read_entry(CacheSection.LIBRARY, "entry", str, str)
        assert entry is not None
        assert entry.meta is None
        assert entry.data == "data"
