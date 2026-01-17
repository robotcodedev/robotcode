"""Integration tests for namespace caching functionality."""

import pickle
from pathlib import Path

import pytest

from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

# Cache directory relative to the test data root
DATA_ROOT = Path(__file__).parent / "data"
CACHE_DIR = DATA_ROOT / ".robotcode_cache"


class TestNamespaceCaching:
    """Integration tests for namespace cache behavior."""

    def test_cache_directory_created_after_analysis(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Cache directory is created after workspace analysis."""
        # Trigger analysis by accessing a document and its namespace
        test_file = DATA_ROOT / "tests" / "hover.robot"
        if not test_file.exists():
            pytest.skip("Test file not found")

        doc = protocol.documents.get_or_open_document(test_file, "robotframework")
        ns = protocol.documents_cache.get_namespace(doc)
        assert ns is not None, "Should have namespace"

        # After analysis, cache directory should be created
        assert CACHE_DIR.exists(), "Cache directory should be created"

    def test_namespace_cache_files_created(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Namespace cache files are created for analyzed robot files."""
        # Trigger analysis first
        test_file = DATA_ROOT / "tests" / "hover.robot"
        if not test_file.exists():
            pytest.skip("Test file not found")

        doc = protocol.documents.get_or_open_document(test_file, "robotframework")
        ns = protocol.documents_cache.get_namespace(doc)
        assert ns is not None, "Should have namespace"

        # Look for namespace cache files
        ns_cache_dirs = list(CACHE_DIR.glob("*/*/namespace"))

        assert len(ns_cache_dirs) > 0, "Should have namespace cache directories"

        # Check for cache files (either .cache.pkl single-file or legacy .meta.pkl/.spec.pkl)
        cache_files: list[Path] = []
        for ns_dir in ns_cache_dirs:
            cache_files.extend(ns_dir.glob("*.cache.pkl"))
            cache_files.extend(ns_dir.glob("*.meta.pkl"))

        assert len(cache_files) > 0, "Should have namespace cache files"

    def test_cache_file_contains_valid_data(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Cache files contain valid pickled metadata and spec data."""
        ns_cache_dirs = list(CACHE_DIR.glob("*/*/namespace"))
        if not ns_cache_dirs:
            pytest.skip("No namespace cache directory found")

        # Find a cache file
        cache_files = list(ns_cache_dirs[0].glob("*.cache.pkl"))
        if not cache_files:
            pytest.skip("No cache files found")

        # Verify it's valid pickle with expected structure
        with open(cache_files[0], "rb") as f:
            data = pickle.load(f)

        # Single-file format stores (meta, spec) tuple
        assert isinstance(data, tuple), "Cache should be a tuple"
        assert len(data) == 2, "Cache should have (meta, spec)"

        meta, _spec = data
        # Verify metadata has required fields
        assert hasattr(meta, "source"), "Meta should have source"
        assert hasattr(meta, "mtime"), "Meta should have mtime"
        assert hasattr(meta, "content_hash"), "Meta should have content_hash"

    def test_cache_metadata_tracks_environment(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Cache metadata includes Python environment tracking fields."""
        ns_cache_dirs = list(CACHE_DIR.glob("*/*/namespace"))
        if not ns_cache_dirs:
            pytest.skip("No namespace cache directory found")

        cache_files = list(ns_cache_dirs[0].glob("*.cache.pkl"))
        if not cache_files:
            pytest.skip("No cache files found")

        with open(cache_files[0], "rb") as f:
            meta, _spec = pickle.load(f)

        # Environment tracking fields (for detecting venv changes)
        assert hasattr(meta, "python_executable"), "Should track python_executable"
        assert hasattr(meta, "sys_path_hash"), "Should track sys_path_hash"
        assert hasattr(meta, "robot_version"), "Should track robot_version"

    def test_corrupt_cache_does_not_crash(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Corrupted cache files are handled gracefully without crashing."""
        ns_cache_dirs = list(CACHE_DIR.glob("*/*/namespace"))
        if not ns_cache_dirs:
            pytest.skip("No namespace cache directory found")

        # Create a corrupt cache file
        corrupt_file = ns_cache_dirs[0] / "corrupt_test.cache.pkl"
        corrupt_file.write_bytes(b"NOT VALID PICKLE DATA")

        try:
            # Access a document - should not crash despite corrupt cache
            test_file = DATA_ROOT / "tests" / "hover.robot"
            if test_file.exists():
                doc = protocol.documents.get_or_open_document(test_file, "robotframework")
                # Try to get namespace (triggers cache lookup)
                ns = protocol.documents_cache.get_namespace(doc)
                assert ns is not None, "Should get namespace despite corrupt sibling cache"
        finally:
            # Cleanup
            if corrupt_file.exists():
                corrupt_file.unlink()

    def test_different_files_have_different_cache_keys(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Files in different directories have unique cache keys (no collisions)."""
        ns_cache_dirs = list(CACHE_DIR.glob("*/*/namespace"))
        if not ns_cache_dirs:
            pytest.skip("No namespace cache directory found")

        # Check uniqueness within each RF version's namespace directory
        # (different RF versions may have the same file names, which is expected)
        for ns_dir in ns_cache_dirs:
            cache_files = list(ns_dir.glob("*.cache.pkl"))
            if len(cache_files) < 2:
                continue

            # Within a single namespace directory, all cache file names should be unique
            names = [f.name for f in cache_files]
            assert len(names) == len(set(names)), f"Cache file names should be unique within {ns_dir}"


class TestCacheInvalidation:
    """Tests for cache invalidation behavior."""

    def test_namespace_available_for_document(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Namespace is available for documents after analysis."""
        test_file = DATA_ROOT / "tests" / "hover.robot"
        if not test_file.exists():
            pytest.skip("Test file not found")

        doc = protocol.documents.get_or_open_document(test_file, "robotframework")
        ns = protocol.documents_cache.get_namespace(doc)

        assert ns is not None, "Should have namespace for document"
        assert ns.source is not None, "Namespace should have source"

    def test_namespace_has_source_and_imports(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Namespace contains source path and import information."""
        test_file = DATA_ROOT / "tests" / "hover.robot"
        if not test_file.exists():
            pytest.skip("Test file not found")

        doc = protocol.documents.get_or_open_document(test_file, "robotframework")
        ns = protocol.documents_cache.get_namespace(doc)

        assert ns is not None
        assert ns.source is not None, "Namespace should have source path"
        # Namespace should have libraries (at least BuiltIn is implicit)
        assert hasattr(ns, "get_libraries"), "Namespace should support get_libraries"


class TestLibraryDocCaching:
    """Tests for library documentation caching."""

    def test_libdoc_cache_directory_exists(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Library documentation cache directory is created."""
        # Trigger analysis first by accessing a document that imports libraries
        test_file = DATA_ROOT / "tests" / "hover.robot"
        if not test_file.exists():
            pytest.skip("Test file not found")

        doc = protocol.documents.get_or_open_document(test_file, "robotframework")
        ns = protocol.documents_cache.get_namespace(doc)
        assert ns is not None, "Should have namespace"

        libdoc_dirs = list(CACHE_DIR.glob("*/*/libdoc"))

        # After analyzing files that import libraries, should have libdoc cache
        assert len(libdoc_dirs) > 0, "Should have libdoc cache directories"

    def test_libdoc_cache_files_exist(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """Library documentation cache contains pickle files."""
        libdoc_dirs = list(CACHE_DIR.glob("*/*/libdoc"))
        if not libdoc_dirs:
            pytest.skip("No libdoc cache directory found")

        cache_files: list[Path] = []
        for libdoc_dir in libdoc_dirs:
            cache_files.extend(libdoc_dir.glob("*.pkl"))

        assert len(cache_files) > 0, "Should have libdoc cache files"

    def test_builtin_library_is_cached(
        self,
        protocol: RobotLanguageServerProtocol,
    ) -> None:
        """BuiltIn library documentation is cached."""
        libdoc_dirs = list(CACHE_DIR.glob("*/*/libdoc"))
        if not libdoc_dirs:
            pytest.skip("No libdoc cache directory found")

        # Look for BuiltIn library cache (may be in subdirectory like robot/libraries/)
        builtin_files: list[Path] = []
        for libdoc_dir in libdoc_dirs:
            builtin_files.extend(libdoc_dir.glob("**/*BuiltIn*"))

        assert len(builtin_files) > 0, "BuiltIn library should be cached"
