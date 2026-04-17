"""Tests for SqliteDataCache file locking."""

import os
import sys
from pathlib import Path

import pytest

from robotcode.robot.diagnostics.data_cache import (
    _LOCK_FILE_NAME,
    CacheSection,
    SqliteDataCache,
    exclusive_cache_lock,
)


class TestSharedLocking:
    def test_lock_file_created_on_open(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)
        assert (cache_dir / _LOCK_FILE_NAME).exists()
        cache.close()

    def test_two_caches_can_open_same_dir(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache1 = SqliteDataCache(cache_dir)
        cache2 = SqliteDataCache(cache_dir)

        cache1.save_entry(CacheSection.LIBRARY, "e1", None, "data1")
        cache2.save_entry(CacheSection.LIBRARY, "e2", None, "data2")

        entry1 = cache2.read_entry(CacheSection.LIBRARY, "e1", str, str)
        assert entry1 is not None
        assert entry1.data == "data1"

        cache1.close()
        cache2.close()

    def test_lock_released_on_close(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)
        cache.close()

        with exclusive_cache_lock(cache_dir) as acquired:
            assert acquired, "Exclusive lock should succeed after cache is closed"


class TestExclusiveLocking:
    def test_exclusive_blocked_by_shared(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)

        with exclusive_cache_lock(cache_dir) as acquired:
            assert not acquired, "Exclusive lock should fail while cache is open"

        cache.close()

    def test_exclusive_blocked_by_multiple_shared(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache1 = SqliteDataCache(cache_dir)
        cache2 = SqliteDataCache(cache_dir)

        with exclusive_cache_lock(cache_dir) as acquired:
            assert not acquired

        cache1.close()

        with exclusive_cache_lock(cache_dir) as acquired:
            assert not acquired

        cache2.close()

        with exclusive_cache_lock(cache_dir) as acquired:
            assert acquired

    def test_exclusive_succeeds_when_no_cache_open(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)
        cache.close()

        with exclusive_cache_lock(cache_dir) as acquired:
            assert acquired

    def test_exclusive_succeeds_when_no_lock_file(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        with exclusive_cache_lock(cache_dir) as acquired:
            assert acquired

    def test_exclusive_lock_held_during_context(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)
        cache.close()

        with exclusive_cache_lock(cache_dir) as acquired:
            assert acquired
            if sys.platform != "win32":
                import fcntl

                fd = os.open(str(cache_dir / _LOCK_FILE_NAME), os.O_RDWR)
                try:
                    with pytest.raises(BlockingIOError):
                        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                finally:
                    os.close(fd)
            else:
                with exclusive_cache_lock(cache_dir) as nested_acquired:
                    assert not nested_acquired


class TestLockingWithPrune:
    def test_prune_safe_when_cache_closed(self, tmp_path: Path) -> None:
        import shutil

        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)
        cache.save_entry(CacheSection.LIBRARY, "e1", None, "data")
        cache.close()

        with exclusive_cache_lock(cache_dir) as acquired:
            assert acquired

        shutil.rmtree(cache_dir)

        assert not cache_dir.exists()

    def test_prune_blocked_when_cache_open(self, tmp_path: Path) -> None:
        cache_dir = tmp_path / "cache"
        cache = SqliteDataCache(cache_dir)

        with exclusive_cache_lock(cache_dir) as acquired:
            assert not acquired
            assert cache_dir.exists()

        cache.close()
