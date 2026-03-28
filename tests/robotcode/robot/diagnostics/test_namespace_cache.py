"""Tests for namespace disk cache integration (1e-e through 1e-h).

Tests for NamespaceMetaData, fingerprint computation, cache validation,
and the disk cache save/load roundtrip via PickleDataCache.
"""

import os
import pickle
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock

from robotcode.robot.diagnostics.data_cache import CacheSection, PickleDataCache
from robotcode.robot.diagnostics.imports_manager import ImportsManager, NamespaceMetaData


@dataclass
class _FakeMeta:
    """Picklable stand-in for LibraryMetaData / RobotFileMeta in tests."""

    name: str = ""
    mtimes: Dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_imports_manager(
    cmd_variables: Optional[Dict[str, str]] = None,
    cmd_variable_files: Optional[List[str]] = None,
    global_library_search_order: Optional[List[str]] = None,
    environment: Optional[Dict[str, str]] = None,
) -> MagicMock:
    """Create a mock ImportsManager with configurable attributes."""
    im = MagicMock()
    im.cmd_variables = cmd_variables or {}
    im.cmd_variable_files = cmd_variable_files or []
    im.global_library_search_order = global_library_search_order or []
    # environment property returns os.environ merged with configured env
    merged_env = dict(os.environ)
    if environment:
        merged_env.update(environment)
    im.environment = merged_env
    # Compute and cache the config fingerprint like ImportsManager does
    im._config_fingerprint = (
        tuple(sorted(im.cmd_variables.items())),
        tuple(im.cmd_variable_files),
        tuple(sorted((k, v) for k, v in im.environment.items() if k not in os.environ)),
        tuple(im.global_library_search_order),
        None,  # languages_fingerprint — no workspace languages in default mock
    )
    im.config_fingerprint = im._config_fingerprint
    # Cached meta lookups return None by default (=> fall back to full get_*_meta)
    im.get_cached_library_meta.return_value = None
    im.get_cached_resource_meta.return_value = None
    im.get_cached_variables_meta.return_value = None
    # Bind real methods so unbound class calls work through the mock
    im.get_resource_meta = ImportsManager.get_resource_meta
    im.compute_dependency_fingerprints = types.MethodType(ImportsManager.compute_dependency_fingerprints, im)
    im.build_namespace_meta = types.MethodType(ImportsManager.build_namespace_meta, im)
    im.validate_namespace_meta = types.MethodType(ImportsManager.validate_namespace_meta, im)
    return im


def _mock_namespace(
    source: str = "/project/test.robot",
    libraries: Optional[Dict[str, str]] = None,
    resources: Optional[Dict[str, str]] = None,
    variables_imports: Optional[Dict[str, str]] = None,
) -> MagicMock:
    """Create a mock Namespace with configurable dependency dicts."""
    ns = MagicMock()
    ns.source = source

    lib_entries = {}
    if libraries:
        for name, lib_doc_source in libraries.items():
            entry = MagicMock()
            entry.import_name = name
            entry.library_doc.source = lib_doc_source
            lib_entries[name] = entry
    ns.libraries = lib_entries

    res_entries = {}
    if resources:
        for name, res_source in resources.items():
            entry = MagicMock()
            entry.import_name = name
            entry.library_doc.source = res_source
            res_entries[name] = entry
    ns.resources = res_entries

    var_entries = {}
    if variables_imports:
        for name, var_source in variables_imports.items():
            entry = MagicMock()
            entry.import_name = name
            entry.library_doc.source = var_source
            var_entries[name] = entry
    ns.variables_imports = var_entries

    return ns


# ===========================================================================
# 1e-e: NamespaceMetaData
# ===========================================================================


class TestNamespaceMetaData:
    def test_filepath_base_includes_adler32_prefix(self) -> None:
        meta = NamespaceMetaData(
            meta_version="1.0",
            source="/project/test.robot",
            source_mtime_ns=1000,
            config_fingerprint=(),
        )
        base = meta.filepath_base
        # Format: 8-hex-digits + underscore + stem + suffix
        assert "_" in base
        assert base.endswith("test.robot")
        assert len(base.split("_", 1)[0]) == 8

    def test_filepath_base_deterministic(self) -> None:
        meta1 = NamespaceMetaData("1.0", "/a/b/c.robot", 0, ())
        meta2 = NamespaceMetaData("2.0", "/a/b/c.robot", 999, ())
        # Same source path -> same filepath_base
        assert meta1.filepath_base == meta2.filepath_base

    def test_filepath_base_differs_for_different_dirs(self) -> None:
        meta1 = NamespaceMetaData("1.0", "/dir1/test.robot", 0, ())
        meta2 = NamespaceMetaData("1.0", "/dir2/test.robot", 0, ())
        assert meta1.filepath_base != meta2.filepath_base

    def test_filepath_base_differs_for_different_files(self) -> None:
        meta1 = NamespaceMetaData("1.0", "/dir/a.robot", 0, ())
        meta2 = NamespaceMetaData("1.0", "/dir/b.robot", 0, ())
        assert meta1.filepath_base != meta2.filepath_base

    def test_meta_pickle_roundtrip(self) -> None:
        meta = NamespaceMetaData(
            meta_version="2.4.0",
            source="/project/test.robot",
            source_mtime_ns=123456789,
            config_fingerprint=(("BROWSER", "chrome"),),
            dependency_fingerprints={
                "lib:BuiltIn": _FakeMeta(name="BuiltIn"),
                "res:/common.resource": _FakeMeta(name="common"),
            },
        )
        restored = pickle.loads(pickle.dumps(meta))
        assert restored == meta

    def test_meta_equality(self) -> None:
        meta1 = NamespaceMetaData("1.0", "/a.robot", 100, ("fp",), {"k": "v"})
        meta2 = NamespaceMetaData("1.0", "/a.robot", 100, ("fp",), {"k": "v"})
        assert meta1 == meta2

    def test_meta_inequality_version(self) -> None:
        meta1 = NamespaceMetaData("1.0", "/a.robot", 100, ())
        meta2 = NamespaceMetaData("2.0", "/a.robot", 100, ())
        assert meta1 != meta2

    def test_meta_inequality_mtime(self) -> None:
        meta1 = NamespaceMetaData("1.0", "/a.robot", 100, ())
        meta2 = NamespaceMetaData("1.0", "/a.robot", 200, ())
        assert meta1 != meta2


# ===========================================================================
# 1e-f: Fingerprint computation
# ===========================================================================


class TestConfigFingerprint:
    def test_deterministic(self) -> None:
        im = _mock_imports_manager(cmd_variables={"BROWSER": "chrome"})
        fp1 = im.config_fingerprint
        fp2 = im.config_fingerprint
        assert fp1 == fp2

    def test_changes_with_variables(self) -> None:
        im1 = _mock_imports_manager(cmd_variables={"BROWSER": "chrome"})
        im2 = _mock_imports_manager(cmd_variables={"BROWSER": "firefox"})
        assert im1.config_fingerprint != im2.config_fingerprint

    def test_changes_with_variable_files(self) -> None:
        im1 = _mock_imports_manager(cmd_variable_files=["vars1.py"])
        im2 = _mock_imports_manager(cmd_variable_files=["vars2.py"])
        assert im1.config_fingerprint != im2.config_fingerprint

    def test_changes_with_search_order(self) -> None:
        im1 = _mock_imports_manager(global_library_search_order=["Lib1"])
        im2 = _mock_imports_manager(global_library_search_order=["Lib2"])
        assert im1.config_fingerprint != im2.config_fingerprint

    def test_returns_tuple(self) -> None:
        im = _mock_imports_manager()
        fp = im.config_fingerprint
        assert isinstance(fp, tuple)

    def test_empty_config(self) -> None:
        im = _mock_imports_manager()
        fp = im.config_fingerprint
        assert isinstance(fp, tuple)


class TestDependencyFingerprints:
    def test_empty_namespace(self) -> None:
        ns = _mock_namespace()
        im = _mock_imports_manager()
        fps = ImportsManager.compute_dependency_fingerprints(im, ns)
        assert fps == {}

    def test_library_fingerprint(self) -> None:
        ns = _mock_namespace(libraries={"BuiltIn": "builtin.py"})
        im = _mock_imports_manager()

        fake_meta = _FakeMeta(name="BuiltIn")
        im.get_library_meta.return_value = (fake_meta, "BuiltIn", False)

        fps = ImportsManager.compute_dependency_fingerprints(im, ns)
        assert "lib:BuiltIn" in fps
        assert fps["lib:BuiltIn"] == fake_meta

    def test_resource_fingerprint(self, tmp_path: Path) -> None:
        resource_file = tmp_path / "common.resource"
        resource_file.write_text("*** Keywords ***\n")

        ns = _mock_namespace(resources={"common.resource": str(resource_file)})
        im = _mock_imports_manager()

        fps = ImportsManager.compute_dependency_fingerprints(im, ns)
        assert f"res:{resource_file}" in fps

    def test_variables_fingerprint(self) -> None:
        ns = _mock_namespace(variables_imports={"vars.py": "vars.py"})
        im = _mock_imports_manager()

        fake_meta = _FakeMeta(name="vars")
        im.get_variables_meta.return_value = (fake_meta, "vars.py")

        fps = ImportsManager.compute_dependency_fingerprints(im, ns)
        assert "var:vars.py" in fps
        assert fps["var:vars.py"] == fake_meta

    def test_library_meta_none_skipped(self) -> None:
        ns = _mock_namespace(libraries={"Unknown": "unknown.py"})
        im = _mock_imports_manager()
        im.get_library_meta.return_value = (None, "Unknown", False)

        fps = ImportsManager.compute_dependency_fingerprints(im, ns)
        assert "lib:Unknown" not in fps

    def test_resource_missing_file_skipped(self) -> None:
        ns = _mock_namespace(resources={"missing": "/nonexistent/file.resource"})
        im = _mock_imports_manager()

        fps = ImportsManager.compute_dependency_fingerprints(im, ns)
        assert len(fps) == 0

    def test_library_meta_exception_skipped(self) -> None:
        ns = _mock_namespace(libraries={"Bad": "bad.py"})
        im = _mock_imports_manager()
        im.get_library_meta.side_effect = RuntimeError("cannot resolve")

        fps = ImportsManager.compute_dependency_fingerprints(im, ns)
        assert "lib:Bad" not in fps


# ===========================================================================
# 1e-f/1e-g: build_namespace_meta + validate_namespace_meta
# ===========================================================================


class TestBuildNamespaceMeta:
    def test_builds_meta_with_correct_fields(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("*** Test Cases ***\n")

        ns = _mock_namespace(source=str(source))
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)
        assert meta.source == str(source)
        assert meta.source_mtime_ns > 0
        assert isinstance(meta.config_fingerprint, tuple)
        assert isinstance(meta.dependency_fingerprints, dict)

    def test_meta_version_set(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(source=str(source))
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)
        assert meta.meta_version  # Non-empty

    def test_missing_source_gets_zero_mtime(self) -> None:
        ns = _mock_namespace(source="/nonexistent/test.robot")
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, "/nonexistent/test.robot", ns)
        assert meta.source_mtime_ns == 0


class TestValidateNamespaceMeta:
    def test_valid_meta_passes(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("*** Test Cases ***\n")

        ns = _mock_namespace(source=str(source))
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)
        assert ImportsManager.validate_namespace_meta(im, meta) is True

    def test_version_mismatch_fails(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(source=str(source))
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)
        meta.meta_version = "0.0.0-invalid"
        assert ImportsManager.validate_namespace_meta(im, meta) is False

    def test_source_mtime_changed_fails(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("original")

        ns = _mock_namespace(source=str(source))
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)

        # Simulate a file modification by shifting the stored mtime.
        # This is more reliable than writing the file again and hoping
        # the filesystem updates the mtime (Windows NTFS has coarse
        # resolution and can keep the same mtime for fast writes).
        meta.source_mtime_ns -= 1
        assert ImportsManager.validate_namespace_meta(im, meta) is False

    def test_source_deleted_fails(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(source=str(source))
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)
        source.unlink()
        assert ImportsManager.validate_namespace_meta(im, meta) is False

    def test_config_fingerprint_changed_fails(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(source=str(source))
        im = _mock_imports_manager(cmd_variables={"BROWSER": "chrome"})

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)

        # Change the configuration
        im2 = _mock_imports_manager(cmd_variables={"BROWSER": "firefox"})
        assert ImportsManager.validate_namespace_meta(im2, meta) is False

    def test_workspace_languages_changed_fails(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(source=str(source))

        # Build meta with Finnish workspace languages
        im = _mock_imports_manager()
        im._config_fingerprint = (
            *im._config_fingerprint[:4],
            (("Oletetaan", "Kun", "Niin"), (), (), (), ()),  # Finnish BDD prefixes
        )
        im.config_fingerprint = im._config_fingerprint

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)

        # Validate with German workspace languages -> should fail
        im2 = _mock_imports_manager()
        im2._config_fingerprint = (
            *im2._config_fingerprint[:4],
            (("Angenommen", "Wenn", "Dann"), (), (), (), ()),  # German BDD prefixes
        )
        im2.config_fingerprint = im2._config_fingerprint

        assert ImportsManager.validate_namespace_meta(im2, meta) is False

    def test_workspace_languages_unchanged_passes(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(source=str(source))

        # Build meta with Finnish workspace languages
        im = _mock_imports_manager()
        lang_fp = (("Oletetaan", "Kun", "Niin"), (), (), (), ())
        im._config_fingerprint = (*im._config_fingerprint[:4], lang_fp)
        im.config_fingerprint = im._config_fingerprint

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)

        # Validate with same languages -> should pass
        im2 = _mock_imports_manager()
        im2._config_fingerprint = (*im2._config_fingerprint[:4], lang_fp)
        im2.config_fingerprint = im2._config_fingerprint

        assert ImportsManager.validate_namespace_meta(im2, meta) is True

    def test_library_dependency_changed_fails(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(source=str(source), libraries={"MyLib": "mylib.py"})
        im = _mock_imports_manager()

        im.get_library_meta.return_value = (_FakeMeta(name="MyLib", mtimes={"/mylib.py": 100}), "MyLib", False)

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)
        assert "lib:MyLib" in meta.dependency_fingerprints

        # Change library meta -> different hash
        im.get_library_meta.return_value = (_FakeMeta(name="MyLib", mtimes={"/mylib.py": 200}), "MyLib", False)

        assert ImportsManager.validate_namespace_meta(im, meta) is False

    def test_resource_dependency_changed_fails(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        res_file = tmp_path / "common.resource"
        res_file.write_text("*** Keywords ***\n")

        ns = _mock_namespace(source=str(source), resources={"common": str(res_file)})
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)

        # Simulate resource file modification by shifting the stored mtime.
        # More reliable than writing the file again (Windows NTFS mtime
        # resolution can cause identical timestamps for fast writes).
        res_key = f"res:{res_file}"
        meta.dependency_fingerprints[res_key].mtime_ns -= 1
        assert ImportsManager.validate_namespace_meta(im, meta) is False

    def test_resource_dependency_deleted_fails(self, tmp_path: Path) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        res_file = tmp_path / "common.resource"
        res_file.write_text("*** Keywords ***\n")

        ns = _mock_namespace(source=str(source), resources={"common": str(res_file)})
        im = _mock_imports_manager()

        meta = ImportsManager.build_namespace_meta(im, str(source), ns)
        res_file.unlink()
        assert ImportsManager.validate_namespace_meta(im, meta) is False


# ===========================================================================
# 1e-g: PickleDataCache integration (save + load roundtrip)
# ===========================================================================


class TestNamespaceMetaCacheRoundtrip:
    def test_save_and_load_meta(self, tmp_path: Path) -> None:
        cache = PickleDataCache(tmp_path / "cache")
        meta = NamespaceMetaData(
            meta_version="2.4.0",
            source="/project/test.robot",
            source_mtime_ns=123456789,
            config_fingerprint=(("BROWSER", "chrome"),),
            dependency_fingerprints={
                "lib:BuiltIn": _FakeMeta(name="BuiltIn"),
                "res:/common.resource": _FakeMeta(name="common"),
            },
        )

        meta_file = meta.filepath_base + ".meta"
        cache.save_cache_data(CacheSection.NAMESPACE, meta_file, meta)

        assert cache.cache_data_exists(CacheSection.NAMESPACE, meta_file)

        loaded = cache.read_cache_data(CacheSection.NAMESPACE, meta_file, NamespaceMetaData)
        assert loaded == meta
        assert loaded.meta_version == "2.4.0"
        assert loaded.dependency_fingerprints == meta.dependency_fingerprints

    def test_cache_section_namespace_exists(self) -> None:
        assert CacheSection.NAMESPACE.value == "namespace"

    def test_different_sources_different_cache_files(self, tmp_path: Path) -> None:
        cache = PickleDataCache(tmp_path / "cache")
        meta1 = NamespaceMetaData("1.0", "/dir1/a.robot", 100, ())
        meta2 = NamespaceMetaData("1.0", "/dir2/b.robot", 200, ())

        cache.save_cache_data(CacheSection.NAMESPACE, meta1.filepath_base + ".meta", meta1)
        cache.save_cache_data(CacheSection.NAMESPACE, meta2.filepath_base + ".meta", meta2)

        loaded1 = cache.read_cache_data(CacheSection.NAMESPACE, meta1.filepath_base + ".meta", NamespaceMetaData)
        loaded2 = cache.read_cache_data(CacheSection.NAMESPACE, meta2.filepath_base + ".meta", NamespaceMetaData)

        assert loaded1.source == "/dir1/a.robot"
        assert loaded2.source == "/dir2/b.robot"
