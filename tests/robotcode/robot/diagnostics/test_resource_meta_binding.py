"""Tests that RESOURCE cache metadata is bound to the content actually parsed.

The disk cache for resource docs must only be consulted or written with a
RobotFileMeta captured from the document's disk state — never from a fresh
stat, which could label older content with a newer file state.
"""

import ast
import types
from pathlib import Path
from typing import Any, Optional

import pytest
from pytest_mock import MockerFixture

from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.path import DiskInfo, normalized_path
from robotcode.robot.diagnostics.data_cache import CacheSection
from robotcode.robot.diagnostics.imports_manager import ImportsManager, RobotFileMeta, _ResourcesEntry


def _make_document(path: Path, disk_info: Optional[DiskInfo]) -> TextDocument:
    return TextDocument(
        document_uri=str(Uri.from_path(path)),
        text="*** Keywords ***\n",
        language_id="robotframework",
        disk_info=disk_info,
    )


class TestRobotFileMetaFromDocument:
    def test_document_with_disk_info_yields_meta(self, tmp_path: Path) -> None:
        path = tmp_path / "common.resource"
        info = DiskInfo(100, 17)
        document = _make_document(path, info)

        meta = RobotFileMeta.from_document(document)

        assert meta is not None
        assert meta.source == str(normalized_path(path))
        assert meta.info == info

    def test_document_without_disk_info_yields_none(self, tmp_path: Path) -> None:
        document = _make_document(tmp_path / "common.resource", None)

        assert RobotFileMeta.from_document(document) is None


class TestResourcesEntryMetaBinding:
    def _make_entry(self, mocker: MockerFixture, document: TextDocument, path: Path) -> _ResourcesEntry:
        parent = mocker.MagicMock()
        parent.documents_manager.get_or_open_document.return_value = document
        return _ResourcesEntry("common.resource", parent, path)

    def test_meta_comes_from_document_disk_state(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "common.resource"
        info = DiskInfo(100, 17)
        entry = self._make_entry(mocker, _make_document(path, info), path)

        entry.get_document()

        assert entry.meta is not None
        assert entry.meta.info == info

    def test_document_without_disk_state_yields_no_meta(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "common.resource"
        entry = self._make_entry(mocker, _make_document(path, None), path)

        entry.get_document()

        assert entry.meta is None

    def test_doc_and_meta_are_returned_together(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "common.resource"
        info = DiskInfo(100, 17)
        document = _make_document(path, info)
        resource_doc = mocker.MagicMock()
        parent = mocker.MagicMock()
        parent.documents_manager.get_or_open_document.return_value = document
        parent.get_resource_doc_from_document.return_value = resource_doc
        entry = _ResourcesEntry("common.resource", parent, path)

        doc, meta = entry.get_resource_doc_with_meta()

        assert doc is resource_doc
        assert meta is not None
        assert meta.info == info


def _bind_get_libdoc_from_model(mocker: MockerFixture) -> Any:
    """MagicMock ImportsManager with the real libdoc-from-model methods bound."""
    im = mocker.MagicMock()
    im._resource_libdoc_cache = {}
    im._model_docs_by_source = {}
    im._logger = mocker.MagicMock()
    im.get_libdoc_from_model = types.MethodType(ImportsManager.get_libdoc_from_model, im)
    im._get_model_doc_cached = types.MethodType(ImportsManager._get_model_doc_cached, im)
    im._save_model_doc_cache = types.MethodType(ImportsManager._save_model_doc_cache, im)
    im.clear_cache = types.MethodType(ImportsManager.clear_cache, im)
    im.remove_cached_resource_docs = types.MethodType(ImportsManager.remove_cached_resource_docs, im)
    return im


class TestGetLibdocFromModelGating:
    def test_no_meta_never_touches_disk_cache(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        built = mocker.MagicMock()
        get_model_doc = mocker.patch("robotcode.robot.diagnostics.imports_manager.get_model_doc", return_value=built)
        model = ast.parse("")

        result = im.get_libdoc_from_model(model, "/project/a.resource", None)

        assert result is built
        get_model_doc.assert_called_once()
        im.data_cache.read_entry.assert_not_called()
        im.data_cache.save_entry.assert_not_called()

    def test_untrusted_meta_never_touches_disk_cache(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        built = mocker.MagicMock()
        mocker.patch("robotcode.robot.diagnostics.imports_manager.get_model_doc", return_value=built)
        meta = RobotFileMeta("/project/a.resource", DiskInfo(100, 17, trusted=False))

        result = im.get_libdoc_from_model(ast.parse(""), "/project/a.resource", meta)

        assert result is built
        im.data_cache.read_entry.assert_not_called()
        im.data_cache.save_entry.assert_not_called()

    def test_trusted_meta_saves_built_doc_under_that_meta(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        im.data_cache.read_entry.return_value = None
        built = mocker.MagicMock()
        mocker.patch("robotcode.robot.diagnostics.imports_manager.get_model_doc", return_value=built)
        meta = RobotFileMeta("/project/a.resource", DiskInfo(100, 17))

        result = im.get_libdoc_from_model(ast.parse(""), "/project/a.resource", meta)

        assert result is built
        save_args = im.data_cache.save_entry.call_args[0]
        assert save_args[1] == meta.source
        assert save_args[2] is meta

    def test_trusted_meta_returns_cached_doc_on_exact_match(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        meta = RobotFileMeta("/project/a.resource", DiskInfo(100, 17))
        cached_entry = mocker.MagicMock()
        cached_entry.meta = RobotFileMeta("/project/a.resource", DiskInfo(100, 17))
        im.data_cache.read_entry.return_value = cached_entry
        get_model_doc = mocker.patch("robotcode.robot.diagnostics.imports_manager.get_model_doc")

        result = im.get_libdoc_from_model(ast.parse(""), "/project/a.resource", meta)

        assert result is cached_entry.data
        get_model_doc.assert_not_called()
        im.data_cache.save_entry.assert_not_called()

    def test_meta_mismatch_rebuilds_instead_of_serving_cached(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        meta = RobotFileMeta("/project/a.resource", DiskInfo(100, 17))
        cached_entry = mocker.MagicMock()
        cached_entry.meta = RobotFileMeta("/project/a.resource", DiskInfo(200, 17))
        im.data_cache.read_entry.return_value = cached_entry
        built = mocker.MagicMock()
        mocker.patch("robotcode.robot.diagnostics.imports_manager.get_model_doc", return_value=built)

        result = im.get_libdoc_from_model(ast.parse(""), "/project/a.resource", meta)

        assert result is built


class TestGetResourceDocFromDocumentDoubleCapture:
    def _bind(self, mocker: MockerFixture) -> Any:
        im = mocker.MagicMock()
        im.get_resource_doc_from_document = types.MethodType(ImportsManager.get_resource_doc_from_document, im)
        return im

    def test_meta_dropped_when_document_changes_during_parse(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "common.resource"
        document = _make_document(path, DiskInfo(100, 17, trusted=False))
        im = self._bind(mocker)

        def parse_and_mutate(doc: TextDocument) -> ast.AST:
            doc.apply_full_change(None, "*** Keywords ***\nChanged\n")
            return ast.parse("")

        im.document_cache_helper.get_resource_model.side_effect = parse_and_mutate

        im.get_resource_doc_from_document(document)

        passed_meta = im.get_libdoc_from_model.call_args[0][2]
        assert passed_meta is None

    def test_meta_passed_through_when_document_is_stable(self, tmp_path: Path, mocker: MockerFixture) -> None:
        path = tmp_path / "common.resource"
        info = DiskInfo(100, 17, trusted=False)
        document = _make_document(path, info)
        im = self._bind(mocker)
        im.document_cache_helper.get_resource_model.return_value = ast.parse("")

        im.get_resource_doc_from_document(document)

        passed_meta = im.get_libdoc_from_model.call_args[0][2]
        assert passed_meta is not None
        assert passed_meta.info == info


class TestDocsOfUnchangedFiles:
    """The doc of a file is kept with the disk state it was read at, so an unchanged file gets the same doc again."""

    SOURCE = "/project/a.resource"

    def _cached_entry(self, mocker: MockerFixture, info: DiskInfo) -> Any:
        entry = mocker.MagicMock()
        entry.meta = RobotFileMeta(self.SOURCE, info)
        return entry

    def test_two_models_of_an_unchanged_file_get_the_same_doc(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        im.data_cache.read_entry.return_value = self._cached_entry(mocker, DiskInfo(100, 17))
        get_model_doc = mocker.patch("robotcode.robot.diagnostics.imports_manager.get_model_doc")

        first = im.get_libdoc_from_model(ast.parse(""), self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))
        second = im.get_libdoc_from_model(ast.parse(""), self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))

        assert second is first
        im.data_cache.read_entry.assert_called_once()
        get_model_doc.assert_not_called()

    def test_a_second_lookup_with_an_equal_meta_does_not_read_the_disk_cache(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        cached_entry = self._cached_entry(mocker, DiskInfo(100, 17))
        im.data_cache.read_entry.return_value = cached_entry

        first = im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))
        second = im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))

        assert first is cached_entry.data
        assert second is first
        im.data_cache.read_entry.assert_called_once()

    @pytest.mark.parametrize("info", [DiskInfo(200, 17), DiskInfo(100, 18)], ids=["mtime", "size"])
    def test_a_lookup_with_another_disk_state_reads_the_disk_cache(self, mocker: MockerFixture, info: DiskInfo) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        im.data_cache.read_entry.return_value = self._cached_entry(mocker, DiskInfo(100, 17))
        im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))
        im.data_cache.read_entry.return_value = self._cached_entry(mocker, info)

        result = im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, info))

        assert im.data_cache.read_entry.call_count == 2
        assert result is im.data_cache.read_entry.return_value.data

    def test_a_saved_doc_is_returned_by_the_next_lookup(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        doc = mocker.MagicMock()
        im._save_model_doc_cache(self.SOURCE, doc, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))

        result = im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))

        assert result is doc
        im.data_cache.read_entry.assert_not_called()

    def test_after_clear_cache_a_lookup_reads_the_disk_cache_again(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        im.data_cache.read_entry.return_value = self._cached_entry(mocker, DiskInfo(100, 17))
        im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))

        im.clear_cache()
        im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))

        assert im.data_cache.read_entry.call_count == 2

    def test_after_removing_the_doc_of_a_file_a_lookup_reads_the_disk_cache_again(self, mocker: MockerFixture) -> None:
        im = _bind_get_libdoc_from_model(mocker)
        im.data_cache.read_entry.return_value = self._cached_entry(mocker, DiskInfo(100, 17))
        im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))

        im.remove_cached_resource_docs([self.SOURCE])
        im._get_model_doc_cached(self.SOURCE, RobotFileMeta(self.SOURCE, DiskInfo(100, 17)))

        assert im.data_cache.read_entry.call_count == 2
        im.data_cache.remove_entries.assert_called_once_with(CacheSection.RESOURCE, [self.SOURCE])
