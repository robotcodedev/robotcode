import pickle
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Tuple, Type, TypeVar, Union, cast

from robotcode.core.utils.dataclasses import as_json, from_json

_T = TypeVar("_T")


class CacheSection(Enum):
    LIBRARY = "libdoc"
    VARIABLES = "variables"


class DataCache(ABC):
    @abstractmethod
    def cache_data_exists(self, section: CacheSection, entry_name: str) -> bool: ...

    @abstractmethod
    def read_cache_data(
        self, section: CacheSection, entry_name: str, types: Union[Type[_T], Tuple[Type[_T], ...]]
    ) -> _T: ...

    @abstractmethod
    def save_cache_data(self, section: CacheSection, entry_name: str, data: Any) -> None: ...


class JsonDataCache(DataCache):
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

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


class PickleDataCache(DataCache):
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

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
