import pickle
import sqlite3
from enum import Enum
from pathlib import Path
from typing import Any, Generic, Optional, Tuple, Type, TypeVar, Union, cast

_M = TypeVar("_M")
_D = TypeVar("_D")


class CacheSection(Enum):
    LIBRARY = "libdoc"
    VARIABLES = "variables"
    RESOURCE = "resource"
    NAMESPACE = "namespace"


class CacheEntry(Generic[_M, _D]):
    """Lazy-deserializing cache entry.

    Meta and data blobs are deserialized on first property access, not when read from DB.
    """

    def __init__(
        self,
        meta_blob: Optional[bytes],
        data_blob: bytes,
        meta_type: Union[Type[_M], Tuple[Type[_M], ...]],
        data_type: Union[Type[_D], Tuple[Type[_D], ...]],
    ) -> None:
        self._meta_blob = meta_blob
        self._data_blob = data_blob
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
            result = pickle.loads(self._data_blob)
            if not isinstance(result, self._data_type):
                raise TypeError(f"Expected {self._data_type} but got {type(result)}")
            self._data_cache = cast(_D, result)
            self._data_loaded = True

        assert self._data_cache is not None
        return self._data_cache


_TABLE_NAMES = [s.value for s in CacheSection]


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
                f"CREATE TABLE IF NOT EXISTS {table} (  entry_name TEXT PRIMARY KEY,  meta BLOB,  data BLOB NOT NULL)"
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
            f"SELECT meta, data FROM {section.value} WHERE entry_name = ?",
            (entry_name,),
        ).fetchone()

        if row is None:
            return None

        return CacheEntry(row[0], row[1], meta_type, data_type)

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
            f"INSERT OR REPLACE INTO {section.value} (entry_name, meta, data) VALUES (?, ?, ?)",
            (entry_name, meta_blob, data_blob),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
