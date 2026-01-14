"""Unit tests for imports_manager cache functionality."""

import zlib
from pathlib import Path

import pytest

from robotcode.robot.diagnostics.imports_manager import (
    RESOURCE_META_VERSION,
    ResourceMetaData,
)


class TestResourceMetaData:
    """Tests for ResourceMetaData dataclass."""

    def test_create_metadata(self) -> None:
        """ResourceMetaData can be created with all required fields."""
        meta = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/to/resource.resource",
            mtime=1234567890123456789,
        )

        assert meta.meta_version == RESOURCE_META_VERSION
        assert meta.source == "/path/to/resource.resource"
        assert meta.mtime == 1234567890123456789

    def test_filepath_base_property(self) -> None:
        """filepath_base computes correct cache filename base."""
        meta = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/home/user/project/resources/common.resource",
            mtime=0,
        )

        # Should be "adler32hash_stem" format
        expected_hash = f"{zlib.adler32(b'/home/user/project/resources'):08x}"
        assert meta.filepath_base == f"{expected_hash}_common"

    def test_filepath_base_different_paths(self) -> None:
        """filepath_base generates unique hashes for different parent directories."""
        meta1 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/a/resource.resource",
            mtime=0,
        )
        meta2 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/b/resource.resource",
            mtime=0,
        )

        # Different parent dirs should produce different hashes
        assert meta1.filepath_base != meta2.filepath_base
        # But both end with the same stem
        assert meta1.filepath_base.endswith("_resource")
        assert meta2.filepath_base.endswith("_resource")

    def test_filepath_base_same_name_different_dirs(self) -> None:
        """Same filename in different directories produces different cache keys."""
        meta1 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/project/tests/keywords.resource",
            mtime=0,
        )
        meta2 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/project/lib/keywords.resource",
            mtime=0,
        )

        assert meta1.filepath_base != meta2.filepath_base

    def test_metadata_equality(self) -> None:
        """ResourceMetaData instances are equal when all fields match."""
        meta1 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/to/resource.resource",
            mtime=12345,
        )
        meta2 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/to/resource.resource",
            mtime=12345,
        )

        assert meta1 == meta2

    def test_metadata_inequality_different_mtime(self) -> None:
        """ResourceMetaData instances differ when mtime differs."""
        meta1 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/to/resource.resource",
            mtime=12345,
        )
        meta2 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/to/resource.resource",
            mtime=67890,
        )

        assert meta1 != meta2

    def test_metadata_inequality_different_source(self) -> None:
        """ResourceMetaData instances differ when source differs."""
        meta1 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/a/resource.resource",
            mtime=12345,
        )
        meta2 = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/path/b/resource.resource",
            mtime=12345,
        )

        assert meta1 != meta2


class TestResourceMetaVersion:
    """Tests for RESOURCE_META_VERSION constant."""

    def test_meta_version_is_string(self) -> None:
        """Meta version is a string."""
        assert isinstance(RESOURCE_META_VERSION, str)
        assert len(RESOURCE_META_VERSION) > 0

    def test_meta_version_value(self) -> None:
        """Meta version has expected value."""
        assert RESOURCE_META_VERSION == "1"


class TestCacheKeyGeneration:
    """Tests for cache key generation patterns."""

    @pytest.mark.parametrize(
        ("source", "expected_stem"),
        [
            ("/path/to/test.resource", "_test"),
            ("/path/to/common_keywords.resource", "_common_keywords"),
            ("/path/to/My-Library.resource", "_My-Library"),
            ("/path/日本語/テスト.resource", "_テスト"),
        ],
    )
    def test_cache_key_stem_extraction(self, source: str, expected_stem: str) -> None:
        """Cache key correctly extracts filename stem."""
        meta = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source=source,
            mtime=0,
        )

        assert meta.filepath_base.endswith(expected_stem)

    def test_cache_key_uses_adler32(self) -> None:
        """Cache key uses zlib.adler32 for parent directory hash."""
        source = "/specific/path/to/resource.resource"
        meta = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source=source,
            mtime=0,
        )

        parent_path = str(Path(source).parent)
        expected_hash = f"{zlib.adler32(parent_path.encode('utf-8')):08x}"

        assert meta.filepath_base.startswith(expected_hash)

    def test_cache_key_hash_length(self) -> None:
        """Cache key hash portion is 8 hex characters (adler32)."""
        meta = ResourceMetaData(
            meta_version=RESOURCE_META_VERSION,
            source="/any/path/file.resource",
            mtime=0,
        )

        hash_part = meta.filepath_base.split("_")[0]
        assert len(hash_part) == 8
        assert all(c in "0123456789abcdef" for c in hash_part)
