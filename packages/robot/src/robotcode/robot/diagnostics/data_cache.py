import pickle
import sqlite3
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Generic, List, Optional, Tuple, Type, TypeVar, Union, cast

from ..utils import get_robot_version_str

_M = TypeVar("_M")
_D = TypeVar("_D")


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
        conn: sqlite3.Connection,
        section: "CacheSection",
        entry_name: str,
        meta_blob: Optional[bytes],
        meta_type: Union[Type[_M], Tuple[Type[_M], ...]],
        data_type: Union[Type[_D], Tuple[Type[_D], ...]],
    ) -> None:
        self._conn = conn
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
                self._meta_cache = cast(_M, result)
            self._meta_loaded = True
        return self._meta_cache

    @property
    def data(self) -> _D:
        if not self._data_loaded:
            row = self._conn.execute(
                f"SELECT data FROM {self._section.value} WHERE entry_name = ?",
                (self._entry_name,),
            ).fetchone()
            if row is None:
                raise RuntimeError(f"Cache entry '{self._entry_name}' disappeared from DB")
            result = pickle.loads(row[0])
            if not isinstance(result, self._data_type):
                raise TypeError(f"Expected {self._data_type} but got {type(result)}")
            self._data_cache = cast(_D, result)
            self._data_loaded = True

        assert self._data_cache is not None
        return self._data_cache


_TABLE_NAMES = [s.value for s in CacheSection]

CACHE_DIR_NAME = ".robotcode_cache"


def build_cache_dir(base_path: Path) -> Path:
    return (
        base_path
        / CACHE_DIR_NAME
        / f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        / get_robot_version_str()
    )


class SqliteDataCache:
    """Cache backend using a single SQLite database with per-section tables.

    Each CacheSection gets its own table with entry_name as PK, plus meta and data
    BLOB columns. An app_version is stored in a metadata table; on version mismatch
    all tables are dropped and recreated.
    """

    def __init__(self, cache_dir: Path, app_version: str = "") -> None:
        self.cache_dir = cache_dir

        if not cache_dir.exists():
            cache_dir.mkdir(parents=True)
            (cache_dir / ".gitignore").write_text(
                "# Created by robotcode\n*\n",
                "utf-8",
            )

        db_path = cache_dir / "cache.db"
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-8000")
        self._conn.execute("PRAGMA mmap_size=67108864")

        self._ensure_schema(app_version)

    def _ensure_schema(self, app_version: str) -> None:
        self._conn.execute("CREATE TABLE IF NOT EXISTS _meta (  key TEXT PRIMARY KEY,  value TEXT NOT NULL)")

        row = self._conn.execute("SELECT value FROM _meta WHERE key = 'app_version'").fetchone()
        stored_version = row[0] if row else None

        if stored_version != app_version:
            for table in _TABLE_NAMES:
                self._conn.execute(f"DROP TABLE IF EXISTS {table}")
            self._conn.execute("INSERT OR REPLACE INTO _meta (key, value) VALUES ('app_version', ?)", (app_version,))

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
        row = self._conn.execute(
            f"SELECT meta FROM {section.value} WHERE entry_name = ?",
            (entry_name,),
        ).fetchone()

        if row is None:
            return None

        return CacheEntry(self._conn, section, entry_name, row[0], meta_type, data_type)

    def save_entry(
        self,
        section: CacheSection,
        entry_name: str,
        meta: Any,
        data: Any,
    ) -> None:
        meta_blob = pickle.dumps(meta, protocol=pickle.HIGHEST_PROTOCOL) if meta is not None else None
        data_blob = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        self._conn.execute(
            f"INSERT INTO {section.value} (entry_name, meta, data)"
            f" VALUES (?, ?, ?)"
            f" ON CONFLICT(entry_name) DO UPDATE SET"
            f" meta = excluded.meta, data = excluded.data, modified_at = CURRENT_TIMESTAMP",
            (entry_name, meta_blob, data_blob),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @property
    def db_path(self) -> Path:
        return self.cache_dir / "cache.db"

    @property
    def app_version(self) -> Optional[str]:
        row = self._conn.execute("SELECT value FROM _meta WHERE key = 'app_version'").fetchone()
        return row[0] if row else None

    def get_section_stats(self, section: CacheSection) -> "SectionStats":
        row = self._conn.execute(
            f"SELECT COUNT(*),"
            f" COALESCE(SUM(LENGTH(meta) + LENGTH(data)), 0),"
            f" MIN(created_at),"
            f" MAX(modified_at)"
            f" FROM {section.value}",
        ).fetchone()
        assert row is not None
        return SectionStats(
            section=section,
            entry_count=row[0],
            total_blob_bytes=row[1],
            oldest_created=row[2],
            newest_modified=row[3],
        )

    def list_entries(self, section: CacheSection) -> List["EntryInfo"]:
        rows = self._conn.execute(
            f"SELECT entry_name, created_at, modified_at,"
            f" LENGTH(meta), LENGTH(data)"
            f" FROM {section.value}"
            f" ORDER BY entry_name",
        ).fetchall()
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
        cursor = self._conn.execute(f"DELETE FROM {section.value}")
        self._conn.commit()
        return cursor.rowcount

    def clear_all(self) -> int:
        total = 0
        for table in _TABLE_NAMES:
            cursor = self._conn.execute(f"DELETE FROM {table}")
            total += cursor.rowcount
        self._conn.commit()
        return total


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
