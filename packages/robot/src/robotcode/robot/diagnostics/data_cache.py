import os
import pickle
import sqlite3
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Generic, Iterator, List, Optional, Tuple, Type, TypeVar, Union

from robotcode.core.utils.logging import LoggingDescriptor

from ..utils import get_robot_version_str

if sys.platform == "win32":
    import ctypes
    import msvcrt
    from ctypes import wintypes
else:
    import fcntl

_M = TypeVar("_M")
_D = TypeVar("_D")
_R = TypeVar("_R")


class CacheSection(Enum):
    LIBRARY = "libdoc"
    VARIABLES = "variables"
    RESOURCE = "resource"
    NAMESPACE = "namespace"


class CacheEntry(Generic[_M, _D]):
    """Lazy cache entry that defers both deserialization and data blob loading.

    Only the meta blob is read from the DB initially. The data blob is fetched
    lazily on first `.data` access, avoiding the transfer of large blobs when
    only meta validation is needed (e.g. on cache misses).
    """

    def __init__(
        self,
        cache: "SqliteDataCache",
        section: "CacheSection",
        entry_name: str,
        meta_blob: Optional[bytes],
        meta_type: Union[Type[_M], Tuple[Type[_M], ...]],
        data_type: Union[Type[_D], Tuple[Type[_D], ...]],
    ) -> None:
        self._cache = cache
        self._section = section
        self._entry_name = entry_name
        self._meta_blob = meta_blob
        self._meta_type = meta_type
        self._data_type = data_type
        self._meta_cache: Optional[_M] = None
        self._data_cache: Optional[_D] = None
        self._meta_loaded = False
        self._data_loaded = False

    @property
    def meta(self) -> Optional[_M]:
        if not self._meta_loaded:
            if self._meta_blob is not None:
                result = pickle.loads(self._meta_blob)
                if not isinstance(result, self._meta_type):
                    raise TypeError(f"Expected {self._meta_type} but got {type(result)}")
                self._meta_cache = result
            self._meta_loaded = True
        return self._meta_cache

    @property
    def data(self) -> _D:
        if not self._data_loaded:
            row = self._cache._fetch_data(self._section, self._entry_name)
            if row is None:
                raise RuntimeError(f"Cache entry '{self._entry_name}' disappeared from DB")
            result = pickle.loads(row[0])
            if not isinstance(result, self._data_type):
                raise TypeError(f"Expected {self._data_type} but got {type(result)}")
            self._data_cache = result
            self._data_loaded = True

        assert self._data_cache is not None
        return self._data_cache


_TABLE_NAMES = [s.value for s in CacheSection]

CACHE_DIR_NAME = ".robotcode_cache"
_LOCK_FILE_NAME = "cache.lock"
_LOCK_LENGTH = 1


if sys.platform == "win32":
    _LOCKFILE_FAIL_IMMEDIATELY = 0x00000001
    _LOCKFILE_EXCLUSIVE_LOCK = 0x00000002
    _ERROR_LOCK_VIOLATION = 33
    _ERROR_IO_PENDING = 997

    class _Overlapped(ctypes.Structure):
        _fields_ = [
            ("Internal", ctypes.c_void_p),
            ("InternalHigh", ctypes.c_void_p),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("hEvent", wintypes.HANDLE),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.LockFileEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_Overlapped),
    ]
    _kernel32.LockFileEx.restype = wintypes.BOOL
    _kernel32.UnlockFileEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_Overlapped),
    ]
    _kernel32.UnlockFileEx.restype = wintypes.BOOL


def _open_lock_file(cache_dir: Path) -> int:
    lock_path = cache_dir / _LOCK_FILE_NAME
    return os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o666)


if sys.platform == "win32":

    def _lock_file(fd: int, *, exclusive: bool, blocking: bool) -> bool:
        flags = 0
        if exclusive:
            flags |= _LOCKFILE_EXCLUSIVE_LOCK
        if not blocking:
            flags |= _LOCKFILE_FAIL_IMMEDIATELY

        overlapped = _Overlapped()
        handle = wintypes.HANDLE(msvcrt.get_osfhandle(fd))
        result = _kernel32.LockFileEx(handle, flags, 0, _LOCK_LENGTH, 0, ctypes.byref(overlapped))
        if result:
            return True

        error = ctypes.get_last_error()
        if not blocking and error in {_ERROR_LOCK_VIOLATION, _ERROR_IO_PENDING}:
            return False

        raise ctypes.WinError(error)

    def _unlock_file(fd: int) -> None:
        overlapped = _Overlapped()
        handle = wintypes.HANDLE(msvcrt.get_osfhandle(fd))
        result = _kernel32.UnlockFileEx(handle, 0, _LOCK_LENGTH, 0, ctypes.byref(overlapped))
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())


else:

    def _lock_file(fd: int, *, exclusive: bool, blocking: bool) -> bool:
        flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        if not blocking:
            flags |= fcntl.LOCK_NB

        try:
            fcntl.flock(fd, flags)
        except OSError:
            if not blocking:
                return False
            raise

        return True

    def _unlock_file(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


def _acquire_shared_lock(cache_dir: Path) -> Optional[int]:
    """Acquire a shared lock on the cache directory."""
    fd = _open_lock_file(cache_dir)
    try:
        _lock_file(fd, exclusive=False, blocking=True)
    except Exception:
        os.close(fd)
        raise
    return fd


def _release_lock(fd: Optional[int]) -> None:
    """Release an advisory lock acquired via _acquire_shared_lock."""
    if fd is None:
        return
    try:
        _unlock_file(fd)
    finally:
        os.close(fd)


@contextmanager
def exclusive_cache_lock(cache_dir: Path) -> Iterator[bool]:
    """Context manager that tries to acquire an exclusive lock on a cache directory.

    Yields True if the lock was acquired (cache is not in use),
    False if another process holds a shared lock (cache is in use).
    The lock is held until the context manager exits.
    """
    lock_path = cache_dir / _LOCK_FILE_NAME
    if not lock_path.exists():
        yield True
        return

    fd = os.open(str(lock_path), os.O_RDWR)
    acquired = False
    try:
        acquired = _lock_file(fd, exclusive=True, blocking=False)
        yield acquired
    finally:
        try:
            if acquired:
                _unlock_file(fd)
        except OSError:
            pass
        os.close(fd)


def resolve_cache_base_path(base_path: Path) -> Path:
    """Apply ROBOTCODE_CACHE_DIR env var override to a cache base path."""
    env_cache_dir = os.environ.get("ROBOTCODE_CACHE_DIR")
    if env_cache_dir:
        return Path(env_cache_dir)
    return base_path


def build_cache_dir(base_path: Path) -> Path:
    return (
        base_path
        / CACHE_DIR_NAME
        / f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        / get_robot_version_str()
    )


# Primary SQLite result codes for an unusable database file.
_SQLITE_CORRUPT = 11
_SQLITE_NOTADB = 26

# Substring markers used to recognize corruption when no error code is available
# (Python < 3.11) or when the error is raised by the sqlite3 module itself rather
# than the engine (e.g. "Could not decode to UTF-8" on a corrupt TEXT column, which
# carries no error code on any version). SQLite error strings are fixed and not
# localized, so substring matching is safe.
_CORRUPTION_MESSAGE_MARKERS = ("malformed", "not a database", "disk image", "corrupt", "decode")


def _is_corruption(exc: sqlite3.DatabaseError) -> bool:
    """Whether the error means the database file itself is corrupt/unusable.

    A locked database, a closed connection (``ProgrammingError``) or a constraint
    violation are *not* corruption and must not trigger a destructive rebuild.
    """
    code = getattr(exc, "sqlite_errorcode", None)  # available since Python 3.11
    if code is not None:
        return (code & 0xFF) in (_SQLITE_CORRUPT, _SQLITE_NOTADB)
    message = str(exc).lower()
    return any(marker in message for marker in _CORRUPTION_MESSAGE_MARKERS)


class SqliteDataCache:
    """Cache backend using a single SQLite database with per-section tables.

    Each CacheSection gets its own table with entry_name as PK, plus meta and data
    BLOB columns. An app_version is stored in a metadata table; on version mismatch
    all tables are dropped and recreated.

    All access to the single shared connection is serialized through a lock, and a
    corrupt database (``sqlite3.DatabaseError``, e.g. "database disk image is
    malformed") is detected and rebuilt from scratch instead of propagating to
    callers.
    """

    _logger = LoggingDescriptor()

    def __init__(self, cache_dir: Path, app_version: str = "") -> None:
        self.cache_dir = cache_dir
        self._app_version = app_version
        self._lock = threading.Lock()

        if not cache_dir.exists():
            cache_dir.mkdir(parents=True)
            (cache_dir / ".gitignore").write_text(
                "# Created by robotcode\n*\n",
                "utf-8",
            )

        self._lock_fd = _acquire_shared_lock(cache_dir)

        try:
            self._open()
        except sqlite3.DatabaseError as e:
            if not _is_corruption(e):
                raise
            self._rebuild()

    def _open(self, *, in_memory: bool = False) -> None:
        """Open the connection, configure it, and ensure the schema exists."""
        self._conn = sqlite3.connect(":memory:" if in_memory else str(self.db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-8000")
        self._conn.execute("PRAGMA busy_timeout=5000")
        # Memory-mapped reads race with a concurrent writer extending the file on
        # macOS/APFS and can persist a torn page ("database disk image is
        # malformed"); keep mmap only where the unified page cache makes it safe.
        self._conn.execute(f"PRAGMA mmap_size={0 if sys.platform == 'darwin' else 67108864}")
        self._ensure_schema()

    def _purge_db_files(self) -> None:
        # Best-effort: on Windows another process (a second editor window) may hold
        # cache.db open, so unlink can raise PermissionError. Failing to delete must
        # not abort recovery - _rebuild falls back to an in-memory cache.
        for suffix in ("", "-wal", "-shm"):
            try:
                (self.cache_dir / f"cache.db{suffix}").unlink(missing_ok=True)
            except OSError:
                pass

    def _rebuild(self) -> None:
        """Discard a corrupt database and reopen an empty one.

        If the corrupt file cannot be removed or reopened (e.g. another process holds
        it open), fall back to a transient in-memory database so the cache stays usable
        for this session instead of taking down the language server.
        """
        self._logger.warning(lambda: f"Cache database {self.db_path} is corrupt, rebuilding it from scratch.")
        conn = getattr(self, "_conn", None)
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        self._purge_db_files()
        try:
            self._open()
        except sqlite3.DatabaseError as e:
            if not _is_corruption(e):
                raise
            self._logger.warning(
                lambda: f"Could not rebuild cache database {self.db_path}; using a temporary in-memory cache."
            )
            self._open(in_memory=True)

    def _run(self, operation: Callable[[], _R]) -> _R:
        """Run a DB operation under the connection lock, rebuilding the cache once if it is corrupt."""
        with self._lock:
            try:
                return operation()
            except sqlite3.DatabaseError as e:
                if not _is_corruption(e):
                    raise
                self._rebuild()
                return operation()

    def _ensure_schema(self) -> None:
        self._conn.execute("CREATE TABLE IF NOT EXISTS _meta (  key TEXT PRIMARY KEY,  value TEXT NOT NULL)")

        row = self._conn.execute("SELECT value FROM _meta WHERE key = 'app_version'").fetchone()
        stored_version = row[0] if row else None

        if stored_version != self._app_version:
            for table in _TABLE_NAMES:
                self._conn.execute(f"DROP TABLE IF EXISTS {table}")
            self._conn.execute(
                "INSERT OR REPLACE INTO _meta (key, value) VALUES ('app_version', ?)", (self._app_version,)
            )

        for table in _TABLE_NAMES:
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                f"  entry_name TEXT PRIMARY KEY,"
                f"  meta BLOB,"
                f"  data BLOB NOT NULL,"
                f"  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                f"  modified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        self._conn.commit()

    def read_entry(
        self,
        section: CacheSection,
        entry_name: str,
        meta_type: Union[Type[_M], Tuple[Type[_M], ...]],
        data_type: Union[Type[_D], Tuple[Type[_D], ...]],
    ) -> Optional[CacheEntry[_M, _D]]:
        row = self._run(
            lambda: self._conn.execute(
                f"SELECT meta FROM {section.value} WHERE entry_name = ?",
                (entry_name,),
            ).fetchone()
        )

        if row is None:
            return None

        return CacheEntry(self, section, entry_name, row[0], meta_type, data_type)

    def _fetch_data(self, section: CacheSection, entry_name: str) -> Optional[Any]:
        return self._run(
            lambda: self._conn.execute(
                f"SELECT data FROM {section.value} WHERE entry_name = ?",
                (entry_name,),
            ).fetchone()
        )

    def save_entry(
        self,
        section: CacheSection,
        entry_name: str,
        meta: Any,
        data: Any,
    ) -> None:
        meta_blob = pickle.dumps(meta, protocol=pickle.HIGHEST_PROTOCOL) if meta is not None else None
        data_blob = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

        def op() -> None:
            self._conn.execute(
                f"INSERT INTO {section.value} (entry_name, meta, data)"
                f" VALUES (?, ?, ?)"
                f" ON CONFLICT(entry_name) DO UPDATE SET"
                f" meta = excluded.meta, data = excluded.data, modified_at = CURRENT_TIMESTAMP",
                (entry_name, meta_blob, data_blob),
            )
            self._conn.commit()

        self._run(op)

    def close(self) -> None:
        with self._lock:
            self._conn.close()
            fd, self._lock_fd = self._lock_fd, None
        _release_lock(fd)

    @property
    def db_path(self) -> Path:
        return self.cache_dir / "cache.db"

    @property
    def app_version(self) -> Optional[str]:
        row = self._run(lambda: self._conn.execute("SELECT value FROM _meta WHERE key = 'app_version'").fetchone())
        return row[0] if row else None

    def get_section_stats(self, section: CacheSection) -> "SectionStats":
        row = self._run(
            lambda: self._conn.execute(
                f"SELECT COUNT(*),"
                f" COALESCE(SUM(LENGTH(meta) + LENGTH(data)), 0),"
                f" MIN(created_at),"
                f" MAX(modified_at)"
                f" FROM {section.value}",
            ).fetchone()
        )
        assert row is not None
        return SectionStats(
            section=section,
            entry_count=row[0],
            total_blob_bytes=row[1],
            oldest_created=row[2],
            newest_modified=row[3],
        )

    def list_entries(self, section: CacheSection) -> List["EntryInfo"]:
        rows = self._run(
            lambda: self._conn.execute(
                f"SELECT entry_name, created_at, modified_at,"
                f" LENGTH(meta), LENGTH(data)"
                f" FROM {section.value}"
                f" ORDER BY entry_name",
            ).fetchall()
        )
        return [
            EntryInfo(
                entry_name=r[0],
                created_at=r[1],
                modified_at=r[2],
                meta_bytes=r[3] or 0,
                data_bytes=r[4] or 0,
            )
            for r in rows
        ]

    def clear_section(self, section: CacheSection) -> int:
        def op() -> int:
            cursor = self._conn.execute(f"DELETE FROM {section.value}")
            self._conn.commit()
            return cursor.rowcount

        return self._run(op)

    def clear_all(self) -> int:
        def op() -> int:
            total = 0
            for table in _TABLE_NAMES:
                cursor = self._conn.execute(f"DELETE FROM {table}")
                total += cursor.rowcount
            self._conn.commit()
            return total

        return self._run(op)


@dataclass
class SectionStats:
    section: CacheSection
    entry_count: int
    total_blob_bytes: int
    oldest_created: Optional[str]
    newest_modified: Optional[str]


@dataclass
class EntryInfo:
    entry_name: str
    created_at: Optional[str]
    modified_at: Optional[str]
    meta_bytes: int
    data_bytes: int
