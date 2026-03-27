import pickle
import sqlite3
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Tuple, Type, TypeVar, Union, cast

from robotcode.core.utils.dataclasses import as_json, from_json

_T = TypeVar("_T")


class CacheSection(Enum):
    LIBRARY = "libdoc"
    VARIABLES = "variables"
    RESOURCE = "resource"
    NAMESPACE = "namespace"


class DataCache(ABC):
    @abstractmethod
    def cache_data_exists(self, section: CacheSection, entry_name: str) -> bool: ...

    @abstractmethod
    def read_cache_data(
        self, section: CacheSection, entry_name: str, types: Union[Type[_T], Tuple[Type[_T], ...]]
    ) -> _T: ...

    @abstractmethod
    def save_cache_data(self, section: CacheSection, entry_name: str, data: Any) -> None: ...

    def close(self) -> None:
        pass


class FileCacheDataBase(DataCache, ABC):
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

        if not Path.exists(self.cache_dir):
            Path.mkdir(self.cache_dir, parents=True)
            Path(self.cache_dir / ".gitignore").write_text(
                "# Created by robotcode\n*\n",
                "utf-8",
            )


class JsonDataCache(FileCacheDataBase):
    def build_cache_data_filename(self, section: CacheSection, entry_name: str) -> Path:
        return self.cache_dir / section.value / (entry_name + ".json")

    def cache_data_exists(self, section: CacheSection, entry_name: str) -> bool:
        cache_file = self.build_cache_data_filename(section, entry_name)
        return cache_file.exists()

    def read_cache_data(
        self, section: CacheSection, entry_name: str, types: Union[Type[_T], Tuple[Type[_T], ...]]
    ) -> _T:
        cache_file = self.build_cache_data_filename(section, entry_name)
        return from_json(cache_file.read_text("utf-8"), types)

    def save_cache_data(self, section: CacheSection, entry_name: str, data: Any) -> None:
        cached_file = self.build_cache_data_filename(section, entry_name)

        cached_file.parent.mkdir(parents=True, exist_ok=True)
        cached_file.write_text(as_json(data), "utf-8")


class PickleDataCache(FileCacheDataBase):
    def build_cache_data_filename(self, section: CacheSection, entry_name: str) -> Path:
        return self.cache_dir / section.value / (entry_name + ".pkl")

    def cache_data_exists(self, section: CacheSection, entry_name: str) -> bool:
        cache_file = self.build_cache_data_filename(section, entry_name)
        return cache_file.exists()

    def read_cache_data(
        self, section: CacheSection, entry_name: str, types: Union[Type[_T], Tuple[Type[_T], ...]]
    ) -> _T:
        cache_file = self.build_cache_data_filename(section, entry_name)

        with cache_file.open("rb") as f:
            result = pickle.load(f)

            if isinstance(result, types):
                return cast(_T, result)

            raise TypeError(f"Expected {types} but got {type(result)}")

    def save_cache_data(self, section: CacheSection, entry_name: str, data: Any) -> None:
        cached_file = self.build_cache_data_filename(section, entry_name)

        cached_file.parent.mkdir(parents=True, exist_ok=True)
        with cached_file.open("wb") as f:
            pickle.dump(data, f)


class SqliteDataCache(DataCache):
    """Cache backend using a single SQLite database with zlib-compressed pickle blobs."""

    _SCHEMA_VERSION = 1

    def __init__(self, cache_dir: Path) -> None:
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
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache_entries ("
            "  section TEXT NOT NULL,"
            "  entry_name TEXT NOT NULL,"
            "  data BLOB NOT NULL,"
            "  PRIMARY KEY (section, entry_name)"
            ")"
        )
        self._conn.commit()

    def cache_data_exists(self, section: CacheSection, entry_name: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM cache_entries WHERE section = ? AND entry_name = ?",
            (section.value, entry_name),
        ).fetchone()
        return row is not None

    def read_cache_data(
        self, section: CacheSection, entry_name: str, types: Union[Type[_T], Tuple[Type[_T], ...]]
    ) -> _T:
        row = self._conn.execute(
            "SELECT data FROM cache_entries WHERE section = ? AND entry_name = ?",
            (section.value, entry_name),
        ).fetchone()

        if row is None:
            raise FileNotFoundError(f"No cache entry for {section.value}/{entry_name}")

        result = pickle.loads(row[0])

        if isinstance(result, types):
            return cast(_T, result)

        raise TypeError(f"Expected {types} but got {type(result)}")

    def save_cache_data(self, section: CacheSection, entry_name: str, data: Any) -> None:
        blob = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        self._conn.execute(
            "INSERT OR REPLACE INTO cache_entries (section, entry_name, data) VALUES (?, ?, ?)",
            (section.value, entry_name, blob),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
