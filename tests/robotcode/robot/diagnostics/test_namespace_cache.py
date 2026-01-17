"""Unit tests for namespace caching data classes and serialization."""

import hashlib
import zlib
from pathlib import Path

import pytest

from robotcode.core.lsp.types import Position, Range
from robotcode.robot.diagnostics.namespace import (
    NAMESPACE_META_VERSION,
    CachedLibraryEntry,
    CachedResourceEntry,
    CachedVariablesEntry,
    Namespace,
    NamespaceCacheData,
    NamespaceMetaData,
)


class TestNamespaceMetaData:
    """Tests for NamespaceMetaData dataclass."""

    def test_create_metadata(self) -> None:
        """NamespaceMetaData can be created with all required fields."""
        meta = NamespaceMetaData(
            meta_version=NAMESPACE_META_VERSION,
            source="/path/to/test.robot",
            mtime=1234567890123456789,
            file_size=1024,
            content_hash="abc123",
            library_sources_mtimes=(("/path/lib.py", 111),),
            resource_sources_mtimes=(("/path/res.resource", 222),),
            variables_sources_mtimes=(("/path/vars.py", 333),),
            robot_version="7.0",
            python_executable="/usr/bin/python3",
            sys_path_hash="def456",
        )

        assert meta.meta_version == NAMESPACE_META_VERSION
        assert meta.source == "/path/to/test.robot"
        assert meta.mtime == 1234567890123456789
        assert meta.file_size == 1024
        assert meta.content_hash == "abc123"

    def test_metadata_is_frozen(self) -> None:
        """NamespaceMetaData is immutable."""
        meta = NamespaceMetaData(
            meta_version=NAMESPACE_META_VERSION,
            source="/path/to/test.robot",
            mtime=1234567890,
            file_size=100,
            content_hash="abc",
            library_sources_mtimes=(),
            resource_sources_mtimes=(),
            variables_sources_mtimes=(),
            robot_version="7.0",
            python_executable="/usr/bin/python3",
            sys_path_hash="def",
        )

        with pytest.raises(AttributeError):
            meta.source = "/other/path"  # type: ignore[misc]

    def test_filepath_base_property(self) -> None:
        """filepath_base computes correct cache filename base."""
        source = "/home/user/project/tests/test_example.robot"
        meta = NamespaceMetaData(
            meta_version=NAMESPACE_META_VERSION,
            source=source,
            mtime=1234567890,
            file_size=100,
            content_hash="abc",
            library_sources_mtimes=(),
            resource_sources_mtimes=(),
            variables_sources_mtimes=(),
            robot_version="7.0",
            python_executable="/usr/bin/python3",
            sys_path_hash="def",
        )

        # Should be "adler32hash_stem" format
        parent_path = str(Path(source).parent)
        expected_hash = f"{zlib.adler32(parent_path.encode('utf-8')):08x}"
        assert meta.filepath_base == f"{expected_hash}_test_example"

    def test_filepath_base_with_different_paths(self) -> None:
        """filepath_base generates unique hashes for different parent directories."""
        meta1 = NamespaceMetaData(
            meta_version=NAMESPACE_META_VERSION,
            source="/path/a/test.robot",
            mtime=0,
            file_size=0,
            content_hash="",
            library_sources_mtimes=(),
            resource_sources_mtimes=(),
            variables_sources_mtimes=(),
            robot_version="7.0",
            python_executable="",
            sys_path_hash="",
        )
        meta2 = NamespaceMetaData(
            meta_version=NAMESPACE_META_VERSION,
            source="/path/b/test.robot",
            mtime=0,
            file_size=0,
            content_hash="",
            library_sources_mtimes=(),
            resource_sources_mtimes=(),
            variables_sources_mtimes=(),
            robot_version="7.0",
            python_executable="",
            sys_path_hash="",
        )

        # Different parent dirs should produce different hashes
        assert meta1.filepath_base != meta2.filepath_base
        # But both end with the same stem
        assert meta1.filepath_base.endswith("_test")
        assert meta2.filepath_base.endswith("_test")


class TestCachedEntryClasses:
    """Tests for cached entry dataclasses."""

    def test_cached_library_entry(self) -> None:
        """CachedLibraryEntry can be created with all fields."""
        entry = CachedLibraryEntry(
            name="Collections",
            import_name="Collections",
            library_doc_source="/path/to/collections.py",
            args=(),
            alias=None,
            import_range=Range(start=Position(line=0, character=0), end=Position(line=0, character=11)),
            import_source="/test.robot",
            alias_range=Range.zero(),
        )

        assert entry.name == "Collections"
        assert entry.import_name == "Collections"
        assert entry.library_doc_source == "/path/to/collections.py"

    def test_cached_library_entry_with_alias(self) -> None:
        """CachedLibraryEntry supports alias."""
        entry = CachedLibraryEntry(
            name="MyAlias",
            import_name="SomeLibrary",
            library_doc_source="/path/to/lib.py",
            args=("arg1", "arg2"),
            alias="MyAlias",
            import_range=Range.zero(),
            import_source="/test.robot",
            alias_range=Range(start=Position(line=0, character=20), end=Position(line=0, character=27)),
        )

        assert entry.alias == "MyAlias"
        assert entry.args == ("arg1", "arg2")

    def test_cached_resource_entry(self) -> None:
        """CachedResourceEntry includes imports and variables."""
        entry = CachedResourceEntry(
            name="common",
            import_name="resources/common.resource",
            library_doc_source="/project/resources/common.resource",
            args=(),
            alias=None,
            import_range=Range.zero(),
            import_source="/test.robot",
            alias_range=Range.zero(),
            imports=(),
            variables=(),
        )

        assert entry.name == "common"
        assert entry.imports == ()
        assert entry.variables == ()

    def test_cached_variables_entry(self) -> None:
        """CachedVariablesEntry includes variables."""
        entry = CachedVariablesEntry(
            name="vars",
            import_name="variables.py",
            library_doc_source="/project/variables.py",
            args=(),
            alias=None,
            import_range=Range.zero(),
            import_source="/test.robot",
            alias_range=Range.zero(),
            variables=(),
        )

        assert entry.name == "vars"
        assert entry.variables == ()

    def test_cached_entries_are_frozen(self) -> None:
        """All cached entry types are immutable."""
        lib_entry = CachedLibraryEntry(
            name="Test",
            import_name="Test",
            library_doc_source=None,
            args=(),
            alias=None,
            import_range=Range.zero(),
            import_source=None,
            alias_range=Range.zero(),
        )

        with pytest.raises(AttributeError):
            lib_entry.name = "Modified"  # type: ignore[misc]


class TestNamespaceCacheData:
    """Tests for NamespaceCacheData dataclass."""

    def test_create_minimal_cache_data(self) -> None:
        """NamespaceCacheData can be created with minimal data."""
        cache_data = NamespaceCacheData(
            libraries=(),
            resources=(),
            resources_files=(),
            variables_imports=(),
            own_variables=(),
            imports=(),
            library_doc=None,
        )

        assert cache_data.libraries == ()
        assert cache_data.analyzed is False
        assert cache_data.diagnostics == ()

    def test_cache_data_with_analysis_results(self) -> None:
        """NamespaceCacheData includes analysis data when analyzed=True."""
        cache_data = NamespaceCacheData(
            libraries=(),
            resources=(),
            resources_files=(),
            variables_imports=(),
            own_variables=(),
            imports=(),
            library_doc=None,
            analyzed=True,
            diagnostics=(),
            test_case_definitions=(),
            tag_definitions=(),
            namespace_references=(),
        )

        assert cache_data.analyzed is True

    def test_cache_data_is_frozen(self) -> None:
        """NamespaceCacheData is immutable."""
        cache_data = NamespaceCacheData(
            libraries=(),
            resources=(),
            resources_files=(),
            variables_imports=(),
            own_variables=(),
            imports=(),
            library_doc=None,
        )

        with pytest.raises(AttributeError):
            cache_data.analyzed = True  # type: ignore[misc]


class TestComputeContentHash:
    """Tests for Namespace._compute_content_hash static method."""

    def test_compute_hash_small_file(self, tmp_path: Path) -> None:
        """Content hash is computed for small files (< 64KB)."""
        test_file = tmp_path / "small.robot"
        content = b"*** Test Cases ***\nTest\n    Log    Hello"
        test_file.write_bytes(content)

        file_size, content_hash = Namespace._compute_content_hash(test_file)

        assert file_size == len(content)
        assert len(content_hash) == 64  # SHA256 hex digest length
        assert content_hash == hashlib.sha256(f"{len(content)}:".encode() + content).hexdigest()

    def test_compute_hash_large_file(self, tmp_path: Path) -> None:
        """Content hash includes first and last 64KB for large files."""
        test_file = tmp_path / "large.robot"
        # Create file > 64KB: 100KB of content
        first_part = b"A" * 65536
        middle_part = b"B" * 20000
        last_part = b"C" * 65536
        content = first_part + middle_part + last_part
        test_file.write_bytes(content)

        file_size, content_hash = Namespace._compute_content_hash(test_file)

        assert file_size == len(content)
        # Verify hash includes size + first 64KB + last 64KB
        expected_hasher = hashlib.sha256()
        expected_hasher.update(f"{len(content)}:".encode())
        expected_hasher.update(first_part)
        expected_hasher.update(content[-65536:])  # Last 64KB
        assert content_hash == expected_hasher.hexdigest()

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Different file content produces different hashes."""
        file1 = tmp_path / "file1.robot"
        file2 = tmp_path / "file2.robot"
        file1.write_bytes(b"Content A")
        file2.write_bytes(b"Content B")

        _, hash1 = Namespace._compute_content_hash(file1)
        _, hash2 = Namespace._compute_content_hash(file2)

        assert hash1 != hash2

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        """Same file content produces same hash."""
        file1 = tmp_path / "file1.robot"
        file2 = tmp_path / "file2.robot"
        content = b"Same content in both files"
        file1.write_bytes(content)
        file2.write_bytes(content)

        _, hash1 = Namespace._compute_content_hash(file1)
        _, hash2 = Namespace._compute_content_hash(file2)

        assert hash1 == hash2

    def test_append_detection(self, tmp_path: Path) -> None:
        """Hash detects appended content (size change)."""
        test_file = tmp_path / "test.robot"
        original = b"Original content"
        test_file.write_bytes(original)
        size1, hash1 = Namespace._compute_content_hash(test_file)

        # Append content
        test_file.write_bytes(original + b"\nAppended line")
        size2, hash2 = Namespace._compute_content_hash(test_file)

        assert size2 > size1
        assert hash1 != hash2

    def test_modification_detection(self, tmp_path: Path) -> None:
        """Hash detects in-place modification (same size, different content)."""
        test_file = tmp_path / "test.robot"
        test_file.write_bytes(b"Original content here")
        _, hash1 = Namespace._compute_content_hash(test_file)

        # Modify without changing size
        test_file.write_bytes(b"Modified content here")
        _, hash2 = Namespace._compute_content_hash(test_file)

        assert hash1 != hash2

    def test_empty_file(self, tmp_path: Path) -> None:
        """Hash handles empty files."""
        test_file = tmp_path / "empty.robot"
        test_file.write_bytes(b"")

        file_size, content_hash = Namespace._compute_content_hash(test_file)

        assert file_size == 0
        assert len(content_hash) == 64


class TestMetaVersion:
    """Tests for namespace meta version constant."""

    def test_meta_version_format(self) -> None:
        """Meta version is a valid version string."""
        assert NAMESPACE_META_VERSION == "1.0"
        # Verify it can be parsed as a version
        parts = NAMESPACE_META_VERSION.split(".")
        assert len(parts) == 2
        assert all(part.isdigit() for part in parts)
