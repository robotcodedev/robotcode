"""Tests for `DocumentsCacheHelper` model caching.

`get_model` returns a model that is cached on (and shared across) the document,
while `get_uncached_model` must always return a fresh, independent model. The
Robocop formatter mutates the model in place, so it relies on the uncached
variant - otherwise the mutations corrupt the shared cached model and repeated
formatting becomes non-idempotent (see
https://github.com/robotcodedev/robotcode/issues/612).
"""

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
from robot.parsing.model.blocks import File

from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.robot.diagnostics.document_cache_helper import DocumentsCacheHelper

TEXT = '*** Test Cases ***\nTest\n    Embedded "args"\n\n\n*** Keywords ***\nEmbedded "${args}"\n    No Operation\n'


@pytest.fixture
def cache_helper() -> DocumentsCacheHelper:
    workspace = MagicMock()
    workspace.get_workspace_folder.return_value = None
    return DocumentsCacheHelper(
        workspace=workspace,
        documents_manager=MagicMock(),
        file_watcher_manager=MagicMock(),
        robot_profile=None,
        analysis_config=None,
    )


def _document(tmp_path: Path, name: str = "test.robot") -> TextDocument:
    return TextDocument(
        document_uri=str(Uri.from_path(tmp_path / name).normalized()),
        language_id="robotframework",
        version=1,
        text=TEXT,
    )


def test_get_model_is_cached_on_the_document(cache_helper: DocumentsCacheHelper, tmp_path: Path) -> None:
    document = _document(tmp_path)

    assert cache_helper.get_model(document) is cache_helper.get_model(document)


@pytest.mark.parametrize("name", ["test.robot", "test.resource", "__init__.robot"])
def test_get_uncached_model_returns_a_fresh_model_every_time(
    cache_helper: DocumentsCacheHelper, tmp_path: Path, name: str
) -> None:
    document = _document(tmp_path, name)

    first = cache_helper.get_uncached_model(document)
    second = cache_helper.get_uncached_model(document)

    assert isinstance(first, File)
    assert first is not second
    assert first is not cache_helper.get_model(document)


def test_uncached_model_mutation_does_not_corrupt_the_cached_model(
    cache_helper: DocumentsCacheHelper,
    tmp_path: Path,
) -> None:
    document = _document(tmp_path)

    cached = cast(File, cache_helper.get_model(document))
    sections_before = len(cached.sections)

    uncached = cast(File, cache_helper.get_uncached_model(document))
    uncached.sections.clear()

    assert len(cached.sections) == sections_before
    assert cache_helper.get_model(document) is cached


# ---------------------------------------------------------------------------
# Namespace disk-cache keying and save gating
# ---------------------------------------------------------------------------


def test_namespace_cache_key_distinguishes_document_types(tmp_path: Path) -> None:
    from robotcode.robot.diagnostics.document_cache_helper import _namespace_cache_key
    from robotcode.robot.diagnostics.namespace import DocumentType

    source = str(tmp_path / "common.robot")

    keys = {
        _namespace_cache_key(source, DocumentType.GENERAL),
        _namespace_cache_key(source, DocumentType.RESOURCE),
        _namespace_cache_key(source, DocumentType.INIT),
        _namespace_cache_key(source, None),
    }

    assert len(keys) == 4
    assert all(key.startswith(source + "\n") for key in keys)


def _saved_document(tmp_path: Path, disk_info: object) -> TextDocument:
    return TextDocument(
        document_uri=str(Uri.from_path(tmp_path / "test.robot").normalized()),
        language_id="robotframework",
        version=None,
        text=TEXT,
        disk_info=disk_info,  # type: ignore[arg-type]
    )


def test_save_namespace_skips_when_meta_is_not_trustworthy(cache_helper: DocumentsCacheHelper, tmp_path: Path) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.namespace import DocumentType

    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    imports_manager.build_namespace_meta.return_value = None

    cache_helper._save_namespace_to_cache(
        str(tmp_path / "test.robot"), document, DocumentType.GENERAL, MagicMock(), imports_manager, disk_info, False
    )

    imports_manager.data_cache.save_entry.assert_not_called()


def test_save_namespace_skips_when_document_changed_during_save(
    cache_helper: DocumentsCacheHelper, tmp_path: Path
) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.namespace import DocumentType

    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    namespace = MagicMock()

    def mutate_and_serialize() -> object:
        document.apply_full_change(None, "changed")
        return MagicMock()

    namespace.to_data.side_effect = mutate_and_serialize

    cache_helper._save_namespace_to_cache(
        str(tmp_path / "test.robot"), document, DocumentType.GENERAL, namespace, imports_manager, disk_info, False
    )

    imports_manager.data_cache.save_entry.assert_not_called()


def test_save_namespace_skips_when_document_opened_during_save(
    cache_helper: DocumentsCacheHelper, tmp_path: Path
) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.namespace import DocumentType

    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    namespace = MagicMock()

    def open_and_serialize() -> object:
        document.version = 1
        return MagicMock()

    namespace.to_data.side_effect = open_and_serialize

    cache_helper._save_namespace_to_cache(
        str(tmp_path / "test.robot"), document, DocumentType.GENERAL, namespace, imports_manager, disk_info, False
    )

    imports_manager.data_cache.save_entry.assert_not_called()


def test_save_namespace_writes_type_keyed_entry(cache_helper: DocumentsCacheHelper, tmp_path: Path) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.document_cache_helper import _namespace_cache_key
    from robotcode.robot.diagnostics.namespace import DocumentType

    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    source = str(tmp_path / "test.robot")

    cache_helper._save_namespace_to_cache(
        source, document, DocumentType.RESOURCE, MagicMock(), imports_manager, disk_info, False
    )

    save_args = imports_manager.data_cache.save_entry.call_args[0]
    assert save_args[1] == _namespace_cache_key(source, DocumentType.RESOURCE)
    assert save_args[2] is imports_manager.build_namespace_meta.return_value


def test_try_load_reads_type_keyed_entry(cache_helper: DocumentsCacheHelper, tmp_path: Path) -> None:
    from robotcode.core.utils.path import DiskInfo
    from robotcode.robot.diagnostics.document_cache_helper import _namespace_cache_key
    from robotcode.robot.diagnostics.namespace import DocumentType

    source_file = tmp_path / "test.robot"
    source_file.write_text(TEXT)
    disk_info = DiskInfo(100, 17)
    document = _saved_document(tmp_path, disk_info)
    imports_manager = MagicMock()
    imports_manager.data_cache.read_entry.return_value = None

    result = cache_helper._try_load_cached_namespace(
        str(source_file), document, DocumentType.RESOURCE, imports_manager, False, disk_info
    )

    assert result is None
    read_args = imports_manager.data_cache.read_entry.call_args[0]
    assert read_args[1] == _namespace_cache_key(str(source_file), DocumentType.RESOURCE)
