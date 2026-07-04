"""Tests that ImportResolver records dependency metadata at resolve time.

The metas are captured atomically with the docs they describe, so a
dependency file changing after resolution can never be fingerprinted with a
newer state than the content that was actually analyzed.
"""

from pathlib import Path
from typing import Any, Optional

from pytest_mock import MockerFixture

from robotcode.core.utils.path import DiskInfo
from robotcode.robot.diagnostics.entities import LibraryImport, ResourceImport, VariablesImport
from robotcode.robot.diagnostics.import_resolver import ImportResolver
from robotcode.robot.diagnostics.imports_manager import RobotFileMeta
from robotcode.robot.diagnostics.library_doc import DEFAULT_LIBRARIES

_SOURCE = "/project/suite.robot"


def _lib_import(name: str) -> LibraryImport:
    return LibraryImport(
        line_no=1, col_offset=0, end_line_no=1, end_col_offset=10, source=_SOURCE, name=name, name_token=None
    )


def _res_import(name: str, source: str = _SOURCE) -> ResourceImport:
    return ResourceImport(
        line_no=2, col_offset=0, end_line_no=2, end_col_offset=10, source=source, name=name, name_token=None
    )


def _var_import(name: str) -> VariablesImport:
    return VariablesImport(
        line_no=3, col_offset=0, end_line_no=3, end_col_offset=10, source=_SOURCE, name=name, name_token=None
    )


def _lib_doc(mocker: MockerFixture, name: str) -> Any:
    doc = mocker.MagicMock()
    doc.name = name
    doc.source = f"/libs/{name}.py"
    doc.source_id = None
    doc.member_name = None
    doc.errors = None
    doc.keywords = [mocker.MagicMock()]
    doc.has_listener = False
    return doc


def _res_doc(mocker: MockerFixture, source: str, source_id: Any = None) -> Any:
    doc = mocker.MagicMock()
    doc.name = Path(source).stem
    doc.source = source
    doc.source_id = source_id
    doc.resource_imports = []
    doc.resource_variables = []
    doc.errors = None
    doc.keywords = [mocker.MagicMock()]
    return doc


def _var_doc(mocker: MockerFixture, source: str) -> Any:
    doc = mocker.MagicMock()
    doc.name = Path(source).stem
    doc.source = source
    doc.source_or_origin = source
    doc.source_id = None
    doc.errors = None
    doc.variables = []
    return doc


def _make_manager(mocker: MockerFixture, lib_meta: Optional[Any] = None) -> Any:
    im = mocker.MagicMock()
    im.get_libdoc_for_library_import_with_meta.side_effect = lambda name, *args, **kwargs: (
        _lib_doc(mocker, name),
        lib_meta,
    )
    return im


def _resolve(mocker: MockerFixture, manager: Any, imports: Any) -> Any:
    resolver = ImportResolver(manager, _SOURCE, mocker.MagicMock(), sentinel=None)
    return resolver.resolve(imports)


class TestLibraryMetas:
    def test_records_meta_under_import_name(self, mocker: MockerFixture) -> None:
        meta = mocker.MagicMock()
        im = _make_manager(mocker, lib_meta=meta)

        resolved = _resolve(mocker, im, [_lib_import("MyLib")])

        assert resolved.dependency_metas["lib:MyLib"] is meta

    def test_records_default_libraries(self, mocker: MockerFixture) -> None:
        meta = mocker.MagicMock()
        im = _make_manager(mocker, lib_meta=meta)

        resolved = _resolve(mocker, im, [])

        for library in DEFAULT_LIBRARIES:
            assert resolved.dependency_metas[f"lib:{library}"] is meta

    def test_records_none_when_no_meta_available(self, mocker: MockerFixture) -> None:
        im = _make_manager(mocker, lib_meta=None)

        resolved = _resolve(mocker, im, [_lib_import("Ignored")])

        assert "lib:Ignored" in resolved.dependency_metas
        assert resolved.dependency_metas["lib:Ignored"] is None


class TestResourceMetas:
    def test_records_meta_under_resolved_source(self, mocker: MockerFixture) -> None:
        im = _make_manager(mocker)
        meta = RobotFileMeta("/project/common.resource", DiskInfo(100, 17))
        im.get_resource_doc_for_resource_import_with_meta.return_value = (
            _res_doc(mocker, "/project/common.resource"),
            meta,
        )

        resolved = _resolve(mocker, im, [_res_import("common.resource")])

        assert resolved.dependency_metas["res:/project/common.resource"] is meta

    def test_reimport_keeps_meta_of_first_resolution(self, mocker: MockerFixture) -> None:
        im = _make_manager(mocker)
        meta1 = RobotFileMeta("/project/common.resource", DiskInfo(100, 17))
        meta2 = RobotFileMeta("/project/common.resource", DiskInfo(200, 18))
        im.get_resource_doc_for_resource_import_with_meta.side_effect = [
            (_res_doc(mocker, "/project/common.resource", source_id=(1, 1)), meta1),
            (_res_doc(mocker, "/project/common.resource", source_id=(1, 1)), meta2),
        ]

        resolved = _resolve(mocker, im, [_res_import("common.resource"), _res_import("common.resource")])

        assert resolved.dependency_metas["res:/project/common.resource"] is meta1

    def test_records_transitively_imported_resources(self, mocker: MockerFixture) -> None:
        im = _make_manager(mocker)
        inner_doc = _res_doc(mocker, "/project/inner.resource")
        inner_meta = RobotFileMeta("/project/inner.resource", DiskInfo(200, 18))
        outer_doc = _res_doc(mocker, "/project/outer.resource")
        outer_doc.resource_imports = [_res_import("inner.resource", source="/project/outer.resource")]
        outer_meta = RobotFileMeta("/project/outer.resource", DiskInfo(100, 17))
        im.get_resource_doc_for_resource_import_with_meta.side_effect = [
            (outer_doc, outer_meta),
            (inner_doc, inner_meta),
        ]

        resolved = _resolve(mocker, im, [_res_import("outer.resource")])

        assert resolved.dependency_metas["res:/project/outer.resource"] is outer_meta
        assert resolved.dependency_metas["res:/project/inner.resource"] is inner_meta

    def test_dirty_resource_recorded_as_none(self, mocker: MockerFixture) -> None:
        im = _make_manager(mocker)
        im.get_resource_doc_for_resource_import_with_meta.return_value = (
            _res_doc(mocker, "/project/common.resource"),
            None,
        )

        resolved = _resolve(mocker, im, [_res_import("common.resource")])

        assert "res:/project/common.resource" in resolved.dependency_metas
        assert resolved.dependency_metas["res:/project/common.resource"] is None


class TestVariablesMetas:
    def test_records_meta_under_import_name(self, mocker: MockerFixture) -> None:
        im = _make_manager(mocker)
        meta = mocker.MagicMock()
        im.get_libdoc_for_variables_import_with_meta.return_value = (_var_doc(mocker, "/project/vars.py"), meta)

        resolved = _resolve(mocker, im, [_var_import("vars.py")])

        assert resolved.dependency_metas["var:vars.py"] is meta
