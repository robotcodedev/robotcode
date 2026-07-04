"""Tests for namespace disk cache integration (1e-e through 1e-h).

Tests for NamespaceMetaData, fingerprint computation, cache validation,
and the disk cache save/load roundtrip via SqliteDataCache.
"""

import os
import pickle
import types
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pytest_mock import MockerFixture

from robotcode.core.utils.path import DiskInfo, normalized_path, probe_disk_info
from robotcode.robot.diagnostics.data_cache import CacheSection, SqliteDataCache
from robotcode.robot.diagnostics.imports_manager import (
    ImportsManager,
    LibraryMetaData,
    NamespaceMetaData,
    RobotFileMeta,
)


def _shift_mtime(info: DiskInfo, delta_ns: int = -1) -> DiskInfo:
    return replace(info, mtime_ns=info.mtime_ns + delta_ns)


def _trusted_info(path: Union[str, Path]) -> DiskInfo:
    """Current DiskInfo of *path*, forced trusted (tmp files are always fresh)."""
    info = probe_disk_info(path)
    assert info is not None
    return replace(info, trusted=True)


def _res_meta(path: Path) -> RobotFileMeta:
    """Trusted RobotFileMeta for a real file, as the resolver would record it."""
    return RobotFileMeta(str(normalized_path(path)), _trusted_info(path))


@dataclass
class _FakeMeta:
    """Picklable stand-in for dependency metadata in cache roundtrip tests.

    Deliberately not a real meta type: build_namespace_meta must fail closed
    for unknown types (see test_unknown_dependency_meta_type_yields_none).
    """

    name: str = ""


def _lib_meta(mtime_ns: int) -> LibraryMetaData:
    return LibraryMetaData("MyLib", None, "/mylib.py", None, True, file_infos={"/mylib.py": DiskInfo(mtime_ns, 1)})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_imports_manager(
    mocker: MockerFixture,
    cmd_variables: Optional[Dict[str, str]] = None,
    cmd_variable_files: Optional[List[str]] = None,
    global_library_search_order: Optional[List[str]] = None,
    environment: Optional[Dict[str, str]] = None,
) -> Any:
    """Create a mock ImportsManager with configurable attributes."""
    im = mocker.MagicMock()
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
    im.get_cached_variables_meta.return_value = None
    # No documents are open (=> resource dependency checks probe the disk)
    im.documents_manager.get.return_value = None
    # Bind real methods so unbound class calls work through the mock
    im.get_resource_meta = ImportsManager.get_resource_meta
    im._is_dependency_meta_trusted = ImportsManager._is_dependency_meta_trusted
    im.build_namespace_meta = types.MethodType(ImportsManager.build_namespace_meta, im)
    im.validate_namespace_meta = types.MethodType(ImportsManager.validate_namespace_meta, im)
    return im


def _mock_namespace(
    mocker: MockerFixture,
    source: str = "/project/test.robot",
    dependency_metas: Optional[Dict[str, Optional[Any]]] = None,
) -> Any:
    """Create a mock Namespace with the dependency metas recorded at resolve time."""
    ns = mocker.MagicMock()
    ns.source = source
    ns.dependency_metas = dependency_metas if dependency_metas is not None else {}
    return ns


# ===========================================================================
# 1e-e: NamespaceMetaData
# ===========================================================================


class TestNamespaceMetaData:
    def test_meta_pickle_roundtrip(self, mocker: MockerFixture) -> None:
        meta = NamespaceMetaData(
            source="/project/test.robot",
            source_info=DiskInfo(123456789, 42),
            config_fingerprint=(("BROWSER", "chrome"),),
            dependency_fingerprints={
                "lib:BuiltIn": _FakeMeta(name="BuiltIn"),
                "res:/common.resource": _FakeMeta(name="common"),
            },
        )
        restored = pickle.loads(pickle.dumps(meta))
        assert restored == meta

    def test_meta_equality(self, mocker: MockerFixture) -> None:
        meta1 = NamespaceMetaData("/a.robot", DiskInfo(100, 1), ("fp",), {"k": "v"})
        meta2 = NamespaceMetaData("/a.robot", DiskInfo(100, 1), ("fp",), {"k": "v"})
        assert meta1 == meta2

    def test_meta_inequality_mtime(self, mocker: MockerFixture) -> None:
        meta1 = NamespaceMetaData("/a.robot", DiskInfo(100, 1), ())
        meta2 = NamespaceMetaData("/a.robot", DiskInfo(200, 1), ())
        assert meta1 != meta2

    def test_meta_inequality_size(self, mocker: MockerFixture) -> None:
        meta1 = NamespaceMetaData("/a.robot", DiskInfo(100, 1), ())
        meta2 = NamespaceMetaData("/a.robot", DiskInfo(100, 2), ())
        assert meta1 != meta2

    def test_meta_default_semantic_model_disabled(self, mocker: MockerFixture) -> None:
        meta = NamespaceMetaData("/a.robot", DiskInfo(100, 1), ())
        assert meta.semantic_model_enabled is False

    def test_meta_inequality_semantic_model_mode(self, mocker: MockerFixture) -> None:
        meta1 = NamespaceMetaData("/a.robot", DiskInfo(100, 1), (), semantic_model_enabled=False)
        meta2 = NamespaceMetaData("/a.robot", DiskInfo(100, 1), (), semantic_model_enabled=True)
        assert meta1 != meta2


# ===========================================================================
# 1e-f: Fingerprint computation
# ===========================================================================


class TestConfigFingerprint:
    def test_deterministic(self, mocker: MockerFixture) -> None:
        im = _mock_imports_manager(mocker, cmd_variables={"BROWSER": "chrome"})
        fp1 = im.config_fingerprint
        fp2 = im.config_fingerprint
        assert fp1 == fp2

    def test_changes_with_variables(self, mocker: MockerFixture) -> None:
        im1 = _mock_imports_manager(mocker, cmd_variables={"BROWSER": "chrome"})
        im2 = _mock_imports_manager(mocker, cmd_variables={"BROWSER": "firefox"})
        assert im1.config_fingerprint != im2.config_fingerprint

    def test_changes_with_variable_files(self, mocker: MockerFixture) -> None:
        im1 = _mock_imports_manager(mocker, cmd_variable_files=["vars1.py"])
        im2 = _mock_imports_manager(mocker, cmd_variable_files=["vars2.py"])
        assert im1.config_fingerprint != im2.config_fingerprint

    def test_changes_with_search_order(self, mocker: MockerFixture) -> None:
        im1 = _mock_imports_manager(mocker, global_library_search_order=["Lib1"])
        im2 = _mock_imports_manager(mocker, global_library_search_order=["Lib2"])
        assert im1.config_fingerprint != im2.config_fingerprint

    def test_returns_tuple(self, mocker: MockerFixture) -> None:
        im = _mock_imports_manager(mocker)
        fp = im.config_fingerprint
        assert isinstance(fp, tuple)

    def test_empty_config(self, mocker: MockerFixture) -> None:
        im = _mock_imports_manager(mocker)
        fp = im.config_fingerprint
        assert isinstance(fp, tuple)


# ===========================================================================
# 1e-f/1e-g: build_namespace_meta + validate_namespace_meta
# ===========================================================================


class TestBuildNamespaceMeta:
    def test_builds_meta_with_correct_fields(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("*** Test Cases ***\n")
        disk_info = _trusted_info(source)

        ns = _mock_namespace(mocker, source=str(source))
        im = _mock_imports_manager(mocker)

        meta = ImportsManager.build_namespace_meta(im, str(source), ns, disk_info)
        assert meta is not None
        assert meta.source == str(source)
        assert meta.source_info == disk_info
        assert isinstance(meta.config_fingerprint, tuple)
        assert isinstance(meta.dependency_fingerprints, dict)
        assert meta.semantic_model_enabled is False

    def test_builds_meta_with_semantic_model_enabled(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("*** Test Cases ***\n")

        ns = _mock_namespace(mocker, source=str(source))
        im = _mock_imports_manager(mocker)

        meta = ImportsManager.build_namespace_meta(
            im, str(source), ns, _trusted_info(source), semantic_model_enabled=True
        )
        assert meta is not None
        assert meta.semantic_model_enabled is True

    def test_uses_recorded_dependency_metas(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")
        recorded = _lib_meta(100)

        ns = _mock_namespace(mocker, source=str(source), dependency_metas={"lib:MyLib": recorded})
        im = _mock_imports_manager(mocker)

        meta = ImportsManager.build_namespace_meta(im, str(source), ns, _trusted_info(source))
        assert meta is not None
        assert meta.dependency_fingerprints == {"lib:MyLib": recorded}

    def test_unknown_dependency_meta_type_yields_none(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Trust dispatch fails closed: unknown meta types must never be persisted."""
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source), dependency_metas={"lib:MyLib": _FakeMeta(name="MyLib")})
        im = _mock_imports_manager(mocker)

        assert ImportsManager.build_namespace_meta(im, str(source), ns, _trusted_info(source)) is None

    def test_untrusted_disk_info_yields_none(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source))
        im = _mock_imports_manager(mocker)

        untrusted = replace(_trusted_info(source), trusted=False)
        assert ImportsManager.build_namespace_meta(im, str(source), ns, untrusted) is None

    def test_missing_dependency_metas_yields_none(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source), dependency_metas=None)
        ns.dependency_metas = None
        im = _mock_imports_manager(mocker)

        assert ImportsManager.build_namespace_meta(im, str(source), ns, _trusted_info(source)) is None

    def test_none_dependency_meta_yields_none(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source), dependency_metas={"res:/dirty.resource": None})
        im = _mock_imports_manager(mocker)

        assert ImportsManager.build_namespace_meta(im, str(source), ns, _trusted_info(source)) is None

    def test_untrusted_resource_meta_yields_none(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")
        res_meta = RobotFileMeta("/project/common.resource", DiskInfo(100, 17, trusted=False))

        ns = _mock_namespace(mocker, source=str(source), dependency_metas={"res:/project/common.resource": res_meta})
        im = _mock_imports_manager(mocker)

        assert ImportsManager.build_namespace_meta(im, str(source), ns, _trusted_info(source)) is None

    def test_untrusted_library_meta_yields_none(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")
        lib_meta = LibraryMetaData(
            "MyLib", None, "/libs/mylib.py", None, True, file_infos={"/libs/mylib.py": DiskInfo(100, 17, trusted=False)}
        )

        ns = _mock_namespace(mocker, source=str(source), dependency_metas={"lib:MyLib": lib_meta})
        im = _mock_imports_manager(mocker)

        assert ImportsManager.build_namespace_meta(im, str(source), ns, _trusted_info(source)) is None


class TestValidateNamespaceMeta:
    def _build(self, im: Any, source: Path, ns: Any) -> NamespaceMetaData:
        meta = ImportsManager.build_namespace_meta(im, str(source), ns, _trusted_info(source))
        assert meta is not None
        return meta

    def test_valid_meta_passes(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("*** Test Cases ***\n")

        ns = _mock_namespace(mocker, source=str(source))
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)
        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is True

    def test_no_source_disk_info_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """A document without a disk snapshot (dirty buffer) must never load from cache."""
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source))
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)
        assert ImportsManager.validate_namespace_meta(im, meta, None) is False

    def test_source_mtime_changed_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("original")

        ns = _mock_namespace(mocker, source=str(source))
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)

        # Simulate a file modification by shifting the stored mtime.
        # This is more reliable than writing the file again and hoping
        # the filesystem updates the mtime (Windows NTFS has coarse
        # resolution and can keep the same mtime for fast writes).
        meta.source_info = _shift_mtime(meta.source_info)
        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is False

    def test_source_size_changed_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("original")

        ns = _mock_namespace(mocker, source=str(source))
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)

        # Same mtime, different size — e.g. a rewrite within the same
        # filesystem timestamp tick.
        meta.source_info = replace(meta.source_info, size=meta.source_info.size + 1)
        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is False

    def test_config_fingerprint_changed_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source))
        im = _mock_imports_manager(mocker, cmd_variables={"BROWSER": "chrome"})

        meta = self._build(im, source, ns)

        # Change the configuration
        im2 = _mock_imports_manager(mocker, cmd_variables={"BROWSER": "firefox"})
        assert ImportsManager.validate_namespace_meta(im2, meta, _trusted_info(source)) is False

    def test_workspace_languages_changed_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source))

        # Build meta with Finnish workspace languages
        im = _mock_imports_manager(mocker)
        im._config_fingerprint = (
            *im._config_fingerprint[:4],
            (("Oletetaan", "Kun", "Niin"), (), (), (), ()),  # Finnish BDD prefixes
        )
        im.config_fingerprint = im._config_fingerprint

        meta = self._build(im, source, ns)

        # Validate with German workspace languages -> should fail
        im2 = _mock_imports_manager(mocker)
        im2._config_fingerprint = (
            *im2._config_fingerprint[:4],
            (("Angenommen", "Wenn", "Dann"), (), (), (), ()),  # German BDD prefixes
        )
        im2.config_fingerprint = im2._config_fingerprint

        assert ImportsManager.validate_namespace_meta(im2, meta, _trusted_info(source)) is False

    def test_workspace_languages_unchanged_passes(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source))

        # Build meta with Finnish workspace languages
        im = _mock_imports_manager(mocker)
        lang_fp = (("Oletetaan", "Kun", "Niin"), (), (), (), ())
        im._config_fingerprint = (*im._config_fingerprint[:4], lang_fp)
        im.config_fingerprint = im._config_fingerprint

        meta = self._build(im, source, ns)

        # Validate with same languages -> should pass
        im2 = _mock_imports_manager(mocker)
        im2._config_fingerprint = (*im2._config_fingerprint[:4], lang_fp)
        im2.config_fingerprint = im2._config_fingerprint

        assert ImportsManager.validate_namespace_meta(im2, meta, _trusted_info(source)) is True

    def test_library_dependency_changed_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source), dependency_metas={"lib:MyLib": _lib_meta(100)})
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)
        assert "lib:MyLib" in meta.dependency_fingerprints

        # Library files changed on disk -> fresh meta differs
        im.get_library_meta.return_value = (_lib_meta(200), "MyLib", False)

        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is False

    def test_library_dependency_unchanged_passes(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        ns = _mock_namespace(mocker, source=str(source), dependency_metas={"lib:MyLib": _lib_meta(100)})
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)

        im.get_library_meta.return_value = (_lib_meta(100), "MyLib", False)

        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is True

    def test_resource_dependency_changed_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        res_file = tmp_path / "common.resource"
        res_file.write_text("*** Keywords ***\n")

        res_meta = _res_meta(res_file)
        ns = _mock_namespace(mocker, source=str(source), dependency_metas={f"res:{res_meta.source}": res_meta})
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)

        # Simulate resource file modification by shifting the stored mtime.
        # More reliable than writing the file again (Windows NTFS mtime
        # resolution can cause identical timestamps for fast writes).
        res_key = f"res:{res_meta.source}"
        fingerprint = meta.dependency_fingerprints[res_key]
        meta.dependency_fingerprints[res_key] = replace(fingerprint, info=_shift_mtime(fingerprint.info))
        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is False

    def test_resource_dependency_deleted_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        res_file = tmp_path / "common.resource"
        res_file.write_text("*** Keywords ***\n")

        res_meta = _res_meta(res_file)
        ns = _mock_namespace(mocker, source=str(source), dependency_metas={f"res:{res_meta.source}": res_meta})
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)
        res_file.unlink()
        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is False

    def test_dirty_open_resource_dependency_fails(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """A resource open in the editor with unsaved changes must fail validation,
        so dependents are rebuilt against the buffer instead of served from disk state."""
        source = tmp_path / "test.robot"
        source.write_text("")

        res_file = tmp_path / "common.resource"
        res_file.write_text("*** Keywords ***\n")

        res_meta = _res_meta(res_file)
        ns = _mock_namespace(mocker, source=str(source), dependency_metas={f"res:{res_meta.source}": res_meta})
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)

        dirty_document = mocker.MagicMock()
        dirty_document.disk_info = None
        im.documents_manager.get.return_value = dirty_document

        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is False

    def test_clean_open_resource_dependency_passes(self, tmp_path: Path, mocker: MockerFixture) -> None:
        source = tmp_path / "test.robot"
        source.write_text("")

        res_file = tmp_path / "common.resource"
        res_file.write_text("*** Keywords ***\n")

        res_meta = _res_meta(res_file)
        ns = _mock_namespace(mocker, source=str(source), dependency_metas={f"res:{res_meta.source}": res_meta})
        im = _mock_imports_manager(mocker)

        meta = self._build(im, source, ns)

        from robotcode.core.text_document import TextDocument
        from robotcode.core.uri import Uri

        clean_document = TextDocument(
            document_uri=str(Uri.from_path(res_file)),
            text=res_file.read_text(),
            language_id="robotframework",
            disk_info=res_meta.info,
        )
        im.documents_manager.get.return_value = clean_document

        assert ImportsManager.validate_namespace_meta(im, meta, _trusted_info(source)) is True


# ===========================================================================
# 1e-g: SqliteDataCache integration (save + load roundtrip)
# ===========================================================================


class TestNamespaceMetaCacheRoundtrip:
    def test_save_and_load_meta(self, tmp_path: Path, mocker: MockerFixture) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        meta = NamespaceMetaData(
            source="/project/test.robot",
            source_info=DiskInfo(123456789, 42),
            config_fingerprint=(("BROWSER", "chrome"),),
            dependency_fingerprints={
                "lib:BuiltIn": _FakeMeta(name="BuiltIn"),
                "res:/common.resource": _FakeMeta(name="common"),
            },
        )

        cache.save_entry(CacheSection.NAMESPACE, meta.source, meta, "dummy_data")

        entry = cache.read_entry(CacheSection.NAMESPACE, meta.source, NamespaceMetaData, str)
        assert entry is not None
        assert entry.meta == meta
        assert entry.meta.dependency_fingerprints == meta.dependency_fingerprints

    def test_cache_section_namespace_exists(self, mocker: MockerFixture) -> None:
        assert CacheSection.NAMESPACE.value == "namespace"

    def test_different_sources_different_cache_entries(self, tmp_path: Path, mocker: MockerFixture) -> None:
        cache = SqliteDataCache(tmp_path / "cache")
        meta1 = NamespaceMetaData("/dir1/a.robot", DiskInfo(100, 1), ())
        meta2 = NamespaceMetaData("/dir2/b.robot", DiskInfo(200, 2), ())

        cache.save_entry(CacheSection.NAMESPACE, meta1.source, meta1, "data1")
        cache.save_entry(CacheSection.NAMESPACE, meta2.source, meta2, "data2")

        entry1 = cache.read_entry(CacheSection.NAMESPACE, meta1.source, NamespaceMetaData, str)
        entry2 = cache.read_entry(CacheSection.NAMESPACE, meta2.source, NamespaceMetaData, str)

        assert entry1 is not None
        assert entry1.meta is not None
        assert entry2 is not None
        assert entry2.meta is not None
        assert entry1.meta.source == "/dir1/a.robot"
        assert entry2.meta.source == "/dir2/b.robot"


# ===========================================================================
# _save_import_cache: persist gate for library/variables metas
# ===========================================================================


class TestSaveImportCacheGate:
    def _im(self, mocker: MockerFixture) -> Any:
        im = mocker.MagicMock()
        im._save_import_cache = types.MethodType(ImportsManager._save_import_cache, im)
        return im

    def _meta(self, trusted: bool) -> LibraryMetaData:
        return LibraryMetaData(
            "MyLib",
            None,
            "/libs/mylib.py",
            None,
            True,
            file_infos={"/libs/mylib.py": DiskInfo(100, 17, trusted=trusted)},
        )

    def test_untrusted_file_infos_skip_persisting(self, mocker: MockerFixture) -> None:
        im = self._im(mocker)

        im._save_import_cache(
            CacheSection.LIBRARY, self._meta(trusted=False), mocker.MagicMock(), "library", "MyLib", ()
        )

        im.data_cache.save_entry.assert_not_called()

    def test_trusted_file_infos_are_persisted(self, mocker: MockerFixture) -> None:
        im = self._im(mocker)
        meta = self._meta(trusted=True)

        im._save_import_cache(CacheSection.LIBRARY, meta, mocker.MagicMock(), "library", "MyLib", ())

        save_args = im.data_cache.save_entry.call_args[0]
        assert save_args[1] == meta.cache_key
        assert save_args[2] is meta
