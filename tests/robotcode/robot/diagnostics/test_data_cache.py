"""Unit tests for data_cache.py - cache implementations."""

import pickle
from dataclasses import dataclass
from pathlib import Path

import pytest

from robotcode.robot.diagnostics.data_cache import (
    CacheSection,
    JsonDataCache,
    PickleDataCache,
)


@dataclass
class SampleData:
    """Sample dataclass for testing serialization."""

    name: str
    value: int


class TestCacheSection:
    """Tests for CacheSection enum."""

    def test_cache_section_values(self) -> None:
        """Verify CacheSection enum has expected values."""
        assert CacheSection.LIBRARY.value == "libdoc"
        assert CacheSection.VARIABLES.value == "variables"
        assert CacheSection.RESOURCE.value == "resource"
        assert CacheSection.NAMESPACE.value == "namespace"


class TestPickleDataCache:
    """Tests for PickleDataCache implementation."""

    def test_init_creates_cache_directory(self, tmp_path: Path) -> None:
        """Cache directory is created on initialization."""
        cache_dir = tmp_path / "cache"
        assert not cache_dir.exists()

        PickleDataCache(cache_dir)

        assert cache_dir.exists()
        assert (cache_dir / ".gitignore").exists()

    def test_init_with_existing_directory(self, tmp_path: Path) -> None:
        """Initialization works with existing directory."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir(parents=True)

        cache = PickleDataCache(cache_dir)

        assert cache.cache_dir == cache_dir

    def test_build_cache_data_filename(self, tmp_path: Path) -> None:
        """Filename is built correctly with section and entry name."""
        cache = PickleDataCache(tmp_path)

        path = cache.build_cache_data_filename(CacheSection.LIBRARY, "test_entry")

        assert path == tmp_path / "libdoc" / "test_entry.pkl"

    def test_cache_data_exists_returns_false_for_missing(self, tmp_path: Path) -> None:
        """cache_data_exists returns False when file doesn't exist."""
        cache = PickleDataCache(tmp_path)

        assert cache.cache_data_exists(CacheSection.LIBRARY, "nonexistent") is False

    def test_cache_data_exists_returns_true_for_existing(self, tmp_path: Path) -> None:
        """cache_data_exists returns True when file exists."""
        cache = PickleDataCache(tmp_path)
        cache.save_cache_data(CacheSection.LIBRARY, "test", {"key": "value"})

        assert cache.cache_data_exists(CacheSection.LIBRARY, "test") is True

    def test_save_and_read_cache_data_dict(self, tmp_path: Path) -> None:
        """Save and read dictionary data correctly."""
        cache = PickleDataCache(tmp_path)
        data = {"name": "test", "values": [1, 2, 3]}

        cache.save_cache_data(CacheSection.LIBRARY, "test", data)
        result = cache.read_cache_data(CacheSection.LIBRARY, "test", dict)

        assert result == data

    def test_save_and_read_cache_data_dataclass(self, tmp_path: Path) -> None:
        """Save and read dataclass correctly."""
        cache = PickleDataCache(tmp_path)
        data = SampleData(name="test", value=42)

        cache.save_cache_data(CacheSection.NAMESPACE, "sample", data)
        result = cache.read_cache_data(CacheSection.NAMESPACE, "sample", SampleData)

        assert result == data

    def test_read_cache_data_type_mismatch_raises_typeerror(self, tmp_path: Path) -> None:
        """TypeError is raised when cached data doesn't match expected type."""
        cache = PickleDataCache(tmp_path)
        cache.save_cache_data(CacheSection.LIBRARY, "test", {"key": "value"})

        with pytest.raises(TypeError, match=r"Expected.*str.*got.*dict"):
            cache.read_cache_data(CacheSection.LIBRARY, "test", str)

    def test_read_cache_data_accepts_tuple_of_types(self, tmp_path: Path) -> None:
        """read_cache_data accepts a tuple of types for validation."""
        cache = PickleDataCache(tmp_path)
        cache.save_cache_data(CacheSection.LIBRARY, "test", {"key": "value"})

        result = cache.read_cache_data(CacheSection.LIBRARY, "test", (dict, list))

        assert result == {"key": "value"}

    def test_read_cache_data_missing_file_raises_error(self, tmp_path: Path) -> None:
        """FileNotFoundError is raised when cache file doesn't exist."""
        cache = PickleDataCache(tmp_path)

        with pytest.raises(FileNotFoundError):
            cache.read_cache_data(CacheSection.LIBRARY, "nonexistent", dict)

    def test_save_creates_section_directory(self, tmp_path: Path) -> None:
        """Section subdirectory is created when saving."""
        cache = PickleDataCache(tmp_path)

        cache.save_cache_data(CacheSection.VARIABLES, "test", {"data": 1})

        assert (tmp_path / "variables").is_dir()

    def test_save_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Existing cache file is overwritten on save."""
        cache = PickleDataCache(tmp_path)
        cache.save_cache_data(CacheSection.LIBRARY, "test", {"version": 1})
        cache.save_cache_data(CacheSection.LIBRARY, "test", {"version": 2})

        result = cache.read_cache_data(CacheSection.LIBRARY, "test", dict)

        assert result == {"version": 2}

    def test_atomic_write_no_temp_files_left(self, tmp_path: Path) -> None:
        """No temporary files are left after successful save."""
        cache = PickleDataCache(tmp_path)
        cache.save_cache_data(CacheSection.LIBRARY, "test", {"data": 1})

        section_dir = tmp_path / "libdoc"
        files = list(section_dir.iterdir())

        assert len(files) == 1
        assert files[0].suffix == ".pkl"

    def test_read_corrupt_pickle_raises_error(self, tmp_path: Path) -> None:
        """UnpicklingError is raised when pickle data is corrupt."""
        cache = PickleDataCache(tmp_path)
        cache_file = cache.build_cache_data_filename(CacheSection.LIBRARY, "corrupt")
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(b"not valid pickle data")

        with pytest.raises((pickle.UnpicklingError, EOFError)):
            cache.read_cache_data(CacheSection.LIBRARY, "corrupt", dict)

    def test_different_sections_are_isolated(self, tmp_path: Path) -> None:
        """Data in different sections doesn't interfere."""
        cache = PickleDataCache(tmp_path)
        cache.save_cache_data(CacheSection.LIBRARY, "same_name", {"section": "library"})
        cache.save_cache_data(CacheSection.RESOURCE, "same_name", {"section": "resource"})

        lib_data = cache.read_cache_data(CacheSection.LIBRARY, "same_name", dict)
        res_data = cache.read_cache_data(CacheSection.RESOURCE, "same_name", dict)

        assert lib_data["section"] == "library"
        assert res_data["section"] == "resource"


class TestJsonDataCache:
    """Tests for JsonDataCache implementation."""

    def test_build_cache_data_filename(self, tmp_path: Path) -> None:
        """Filename uses .json extension."""
        cache = JsonDataCache(tmp_path)

        path = cache.build_cache_data_filename(CacheSection.LIBRARY, "test_entry")

        assert path == tmp_path / "libdoc" / "test_entry.json"

    def test_cache_data_exists(self, tmp_path: Path) -> None:
        """cache_data_exists works for JSON cache."""
        cache = JsonDataCache(tmp_path)

        assert cache.cache_data_exists(CacheSection.LIBRARY, "test") is False

        cache.save_cache_data(CacheSection.LIBRARY, "test", {"key": "value"})

        assert cache.cache_data_exists(CacheSection.LIBRARY, "test") is True

    def test_save_and_read_cache_data(self, tmp_path: Path) -> None:
        """Save and read JSON data correctly."""
        cache = JsonDataCache(tmp_path)
        data = {"name": "test", "values": [1, 2, 3]}

        cache.save_cache_data(CacheSection.LIBRARY, "test", data)
        result = cache.read_cache_data(CacheSection.LIBRARY, "test", dict)

        assert result == data


class TestCacheEdgeCases:
    """Edge case tests for cache implementations."""

    @pytest.mark.parametrize(
        "entry_name",
        [
            "simple",
            "with_underscore",
            "with-dash",
            "with.dots",
            "nested/path/entry",
            "unicode_日本語",
        ],
    )
    def test_various_entry_names(self, tmp_path: Path, entry_name: str) -> None:
        """Cache handles various entry name formats."""
        cache = PickleDataCache(tmp_path)
        data = {"entry": entry_name}

        cache.save_cache_data(CacheSection.LIBRARY, entry_name, data)
        result = cache.read_cache_data(CacheSection.LIBRARY, entry_name, dict)

        assert result == data

    def test_large_data(self, tmp_path: Path) -> None:
        """Cache handles large data objects."""
        cache = PickleDataCache(tmp_path)
        # Create ~1MB of data
        data = {"items": list(range(100000)), "text": "x" * 500000}

        cache.save_cache_data(CacheSection.NAMESPACE, "large", data)
        result = cache.read_cache_data(CacheSection.NAMESPACE, "large", dict)

        assert result == data

    def test_none_value(self, tmp_path: Path) -> None:
        """Cache handles None values."""
        cache = PickleDataCache(tmp_path)

        cache.save_cache_data(CacheSection.LIBRARY, "none_test", None)
        result = cache.read_cache_data(CacheSection.LIBRARY, "none_test", type(None))

        assert result is None

    def test_empty_dict(self, tmp_path: Path) -> None:
        """Cache handles empty dictionaries."""
        cache = PickleDataCache(tmp_path)

        cache.save_cache_data(CacheSection.LIBRARY, "empty", {})
        result = cache.read_cache_data(CacheSection.LIBRARY, "empty", dict)

        assert result == {}
