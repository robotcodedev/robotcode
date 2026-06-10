"""Tests for SqliteDataCache backend."""

import os
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple

import pytest

from robotcode.robot.diagnostics.data_cache import (
    CacheEntry,
    CacheSection,
    SqliteDataCache,
    _is_corruption,
)


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

        class _CacheStub:
            def _fetch_data(self, section: CacheSection, entry_name: str) -> Any:
                return conn.execute(
                    f"SELECT data FROM {section.value} WHERE entry_name = ?",
                    (entry_name,),
                ).fetchone()

        cache = _CacheStub()
        return CacheEntry(cache, CacheSection.LIBRARY, "test_entry", meta_blob, meta_type, data_type)  # type: ignore[arg-type]

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

    def test_clear_all_removes_entries(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_entry(CacheSection.LIBRARY, "a", None, "x")
        cache.save_entry(CacheSection.RESOURCE, "b", None, "y")

        assert cache.clear_all() == 2
        assert cache.read_entry(CacheSection.LIBRARY, "a", str, str) is None
        assert cache.read_entry(CacheSection.RESOURCE, "b", str, str) is None

    def test_clear_section_removes_only_that_section(self, tmp_path: Path) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_entry(CacheSection.LIBRARY, "a", None, "x")
        cache.save_entry(CacheSection.RESOURCE, "b", None, "y")

        assert cache.clear_section(CacheSection.LIBRARY) == 1
        assert cache.read_entry(CacheSection.LIBRARY, "a", str, str) is None
        assert cache.read_entry(CacheSection.RESOURCE, "b", str, str) is not None


class TestCorruptionRecovery:
    """A corrupt cache.db must be detected and rebuilt, never propagated to callers (issue #614)."""

    def test_unreadable_db_on_open_is_rebuilt(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)
        cache.save_entry(CacheSection.LIBRARY, "entry", None, "old")
        cache.close()

        # A completely unusable file makes even ``PRAGMA journal_mode=WAL`` raise,
        # i.e. the corruption surfaces during connect, before schema setup.
        (cache_dir / "cache.db").write_bytes(b"this is not a database" * 100)

        # Opening must not raise; the corrupt db is discarded and rebuilt empty.
        cache2 = SqliteDataCache(cache_dir)
        assert cache2.read_entry(CacheSection.LIBRARY, "entry", str, str) is None
        cache2.save_entry(CacheSection.LIBRARY, "fresh", None, "new")
        entry = cache2.read_entry(CacheSection.LIBRARY, "fresh", str, str)
        assert entry is not None
        assert entry.data == "new"
        cache2.close()

    def test_corrupt_pages_on_open_are_rebuilt(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir, app_version="1.0.0")
        for i in range(200):
            cache.save_entry(CacheSection.NAMESPACE, f"entry{i}", None, {"i": i})
        cache.close()

        # A valid header but garbage b-tree pages -> "database disk image is malformed"
        # on read. Overwrite from the second page onward so the header stays intact.
        db_file = cache_dir / "cache.db"
        with db_file.open("r+b") as f:
            f.seek(4096)
            f.write(os.urandom(16384))

        cache2 = SqliteDataCache(cache_dir, app_version="1.0.0")
        # Reads degrade gracefully and the cache stays usable afterwards.
        cache2.save_entry(CacheSection.NAMESPACE, "after", None, {"ok": True})
        entry = cache2.read_entry(CacheSection.NAMESPACE, "after", str, dict)
        assert entry is not None
        assert entry.data == {"ok": True}
        cache2.close()

    def test_run_rebuilds_on_runtime_corruption(self, tmp_path: Path) -> None:
        import sqlite3

        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_entry(CacheSection.LIBRARY, "entry", None, "data")

        class _BoomConnection:
            """Stand-in connection whose queries fail like a corrupt database."""

            def execute(self, *args: object, **kwargs: object) -> object:
                raise sqlite3.DatabaseError("database disk image is malformed")

            def close(self) -> None:
                pass

        # Simulate the live connection turning corrupt mid-session.
        cache._conn = _BoomConnection()  # type: ignore[assignment]

        # The read must not raise: _run detects the error, rebuilds, and retries.
        assert cache.read_entry(CacheSection.LIBRARY, "entry", str, str) is None

        # The cache is functional again on the rebuilt database.
        cache.save_entry(CacheSection.LIBRARY, "again", None, "v")
        entry = cache.read_entry(CacheSection.LIBRARY, "again", str, str)
        assert entry is not None
        assert entry.data == "v"
        cache.close()

    def test_clear_all_recovers_from_corruption(self, tmp_path: Path) -> None:
        import sqlite3

        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_entry(CacheSection.LIBRARY, "entry", None, "data")

        class _BoomConnection:
            def execute(self, *args: object, **kwargs: object) -> object:
                raise sqlite3.DatabaseError("database disk image is malformed")

            def close(self) -> None:
                pass

        cache._conn = _BoomConnection()  # type: ignore[assignment]

        # clear_all is the path the "Clear Cache" command hits; it must recover, not raise.
        assert cache.clear_all() == 0
        cache.save_entry(CacheSection.LIBRARY, "fresh", None, "v")
        entry = cache.read_entry(CacheSection.LIBRARY, "fresh", str, str)
        assert entry is not None
        assert entry.data == "v"
        cache.close()

    def test_non_corruption_error_does_not_purge(self, tmp_path: Path) -> None:
        import sqlite3

        cache = SqliteDataCache(tmp_path / "cache")
        cache.save_entry(CacheSection.LIBRARY, "keep", None, "data")
        real_conn = cache._conn

        class _ClosedConnection:
            """A closed connection raises ProgrammingError - a DatabaseError that is NOT corruption."""

            def execute(self, *args: object, **kwargs: object) -> object:
                raise sqlite3.ProgrammingError("Cannot operate on a closed database.")

            def close(self) -> None:
                pass

        cache._conn = _ClosedConnection()  # type: ignore[assignment]

        # A non-corruption error must propagate, not silently wipe the cache.
        with pytest.raises(sqlite3.ProgrammingError):
            cache.read_entry(CacheSection.LIBRARY, "keep", str, str)

        # The on-disk data is untouched: restoring the real connection still finds it.
        cache._conn = real_conn
        entry = cache.read_entry(CacheSection.LIBRARY, "keep", str, str)
        assert entry is not None
        assert entry.data == "data"
        cache.close()

    def test_decode_error_on_open_is_rebuilt(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir, app_version="1.0.0")
        cache.save_entry(CacheSection.LIBRARY, "entry", None, "old")
        cache.close()

        # Corrupt the stored app_version TEXT to invalid UTF-8 (the page stays
        # structurally valid). Reading it raises OperationalError "Could not decode to
        # UTF-8" inside _ensure_schema during the constructor - a corruption variant
        # that carries no SQLite error code on any Python version.
        db_file = cache_dir / "cache.db"
        raw = bytearray(db_file.read_bytes())
        idx = raw.find(b"1.0.0")
        assert idx != -1, "expected app_version to be checkpointed into the main db file"
        raw[idx : idx + 5] = b"\xff\xfe\xff\xfe\xff"
        db_file.write_bytes(bytes(raw))

        # Construction must not raise; the cache is rebuilt and usable.
        cache2 = SqliteDataCache(cache_dir, app_version="1.0.0")
        assert cache2.read_entry(CacheSection.LIBRARY, "entry", str, str) is None
        cache2.save_entry(CacheSection.LIBRARY, "fresh", None, "new")
        entry = cache2.read_entry(CacheSection.LIBRARY, "fresh", str, str)
        assert entry is not None
        assert entry.data == "new"
        cache2.close()

    def test_falls_back_to_in_memory_when_corrupt_file_cannot_be_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cache_dir = tmp_path / "cache"
        SqliteDataCache(cache_dir).close()

        # Make the on-disk db unusable ...
        (cache_dir / "cache.db").write_bytes(b"not a database" * 100)

        # ... and impossible to delete, as if another process held it open on Windows.
        original_unlink = Path.unlink

        def deny_unlink(self: Path, *args: object, **kwargs: object) -> None:
            if self.name.startswith("cache.db"):
                raise PermissionError("file is held open by another process")
            original_unlink(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "unlink", deny_unlink)

        # Construction must not raise; it degrades to a transient in-memory cache.
        cache = SqliteDataCache(cache_dir)
        cache.save_entry(CacheSection.LIBRARY, "x", None, "v")
        entry = cache.read_entry(CacheSection.LIBRARY, "x", str, str)
        assert entry is not None
        assert entry.data == "v"
        cache.close()


class TestIsCorruption:
    """The classifier must rebuild only on real corruption, never on locks/closes/constraints."""

    def test_corrupt_error_codes_are_corruption(self) -> None:
        for code in (11, 26):  # SQLITE_CORRUPT, SQLITE_NOTADB
            exc = sqlite3.DatabaseError("boom")
            setattr(exc, "sqlite_errorcode", code)
            assert _is_corruption(exc) is True

    def test_extended_corrupt_error_code_is_corruption(self) -> None:
        # Extended result codes keep the primary code in the low byte
        # (e.g. SQLITE_CORRUPT_VTAB == 11 | (1 << 8)).
        exc = sqlite3.DatabaseError("boom")
        setattr(exc, "sqlite_errorcode", 11 | (1 << 8))
        assert _is_corruption(exc) is True

    def test_transient_error_codes_are_not_corruption(self) -> None:
        for code in (5, 19):  # SQLITE_BUSY (locked), SQLITE_CONSTRAINT
            exc = sqlite3.DatabaseError("boom")
            setattr(exc, "sqlite_errorcode", code)
            assert _is_corruption(exc) is False

    def test_error_code_takes_precedence_over_message(self) -> None:
        # A transient error whose message happens to contain a marker must not be
        # treated as corruption when the authoritative error code says otherwise.
        exc = sqlite3.DatabaseError("disk image is locked")
        setattr(exc, "sqlite_errorcode", 5)
        assert _is_corruption(exc) is False

    def test_message_fallback_recognizes_corruption(self) -> None:
        # No error code (Python < 3.11, or errors raised by the sqlite3 module itself).
        for message in (
            "database disk image is malformed",
            "file is not a database",
            "database corruption at line 12345",
            "Could not decode to UTF-8 column 'v' with text '...'",
        ):
            assert _is_corruption(sqlite3.DatabaseError(message)) is True, message

    def test_message_fallback_rejects_transient_errors(self) -> None:
        for message in (
            "database is locked",
            "Cannot operate on a closed database.",
            "UNIQUE constraint failed: libdoc.entry_name",
        ):
            assert _is_corruption(sqlite3.DatabaseError(message)) is False, message


class TestConcurrency:
    """The connection is shared across threads (check_same_thread=False); the lock must serialize it."""

    def test_concurrent_read_write_is_safe(self, tmp_path: Path) -> None:
        import random

        cache = SqliteDataCache(tmp_path / "cache")
        # Pre-populate so every read finds its entry (avoids the benign, caller-handled
        # "disappeared from DB" race that a concurrent clear would introduce).
        keys = [f"k{i}" for i in range(20)]
        for k in keys:
            cache.save_entry(CacheSection.LIBRARY, k, {"m": k}, {"d": [k] * 10})

        errors: List[Tuple[int, str, str]] = []
        start = threading.Barrier(8)

        def worker(tid: int) -> None:
            rnd = random.Random(tid)
            start.wait()
            try:
                for _ in range(200):
                    k = rnd.choice(keys)
                    if rnd.random() < 0.5:
                        cache.save_entry(CacheSection.LIBRARY, k, {"m": tid}, {"d": [tid] * 10})
                    else:
                        entry = cache.read_entry(CacheSection.LIBRARY, k, dict, dict)
                        if entry is not None and entry.meta is not None:
                            _ = entry.data  # forces the cross-thread _fetch_data -> _run path
            except BaseException as ex:
                errors.append((tid, type(ex).__name__, str(ex)))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"concurrent access raised: {errors[:5]}"

        # The cache still works after the storm.
        cache.save_entry(CacheSection.LIBRARY, "sentinel", None, "ok")
        sentinel = cache.read_entry(CacheSection.LIBRARY, "sentinel", str, str)
        assert sentinel is not None
        assert sentinel.data == "ok"
        cache.close()
