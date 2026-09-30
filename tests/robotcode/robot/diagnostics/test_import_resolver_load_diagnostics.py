"""Tests for the diagnostics ImportResolver reports for library loads that failed.

The imports manager is mocked, so the tests only check how the resolver
reports the errors of the documents it gets.
"""

from typing import Any, List

from pytest_mock import MockerFixture

from robotcode.core.lsp.types import DiagnosticSeverity, Range
from robotcode.robot.diagnostics.entities import LibraryImport, ResourceImport
from robotcode.robot.diagnostics.errors import Error as DiagnosticError
from robotcode.robot.diagnostics.import_resolver import ImportResolver
from robotcode.robot.diagnostics.library_doc import Error

_SOURCE = "/project/suite.robot"

_TIMEOUT_MESSAGE = (
    "Loading library 'BuiltIn' with args () timed out after 1 seconds. The import may be slow or blocked. "
    "If required, increase the timeout by setting the ROBOTCODE_LOAD_LIBRARY_TIMEOUT environment variable."
)


def _lib_doc(mocker: MockerFixture, name: str, errors: Any = None, loaded_without_arguments: bool = False) -> Any:
    doc = mocker.MagicMock()
    doc.name = name
    doc.source = f"/libs/{name}.py"
    doc.source_id = None
    doc.member_name = None
    doc.errors = errors
    doc.keywords = [mocker.MagicMock()] if loaded_without_arguments or not errors else []
    doc.has_listener = False
    doc.loaded_without_arguments = loaded_without_arguments
    return doc


def _resolve(mocker: MockerFixture, manager: Any, imports: List[Any]) -> Any:
    resolver = ImportResolver(manager, _SOURCE, mocker.MagicMock(), sentinel=None)
    return resolver.resolve(imports)


class TestDefaultLibraries:
    def test_errors_of_a_default_library_document_are_reported(self, mocker: MockerFixture) -> None:
        im = mocker.MagicMock()
        im.get_libdoc_for_library_import_with_meta.side_effect = lambda name, *args, **kwargs: (
            _lib_doc(
                mocker,
                name,
                [Error(message=_TIMEOUT_MESSAGE, type_name=DiagnosticError.LIBRARY_TIMEOUT_ERROR)]
                if name == "BuiltIn"
                else None,
            ),
            None,
        )

        resolved = _resolve(mocker, im, [])

        diagnostics = [d for d in resolved.diagnostics if "default library" in d.message]
        assert len(diagnostics) == 1
        assert diagnostics[0].message == f"Can't import default library 'BuiltIn': {_TIMEOUT_MESSAGE}"
        assert diagnostics[0].code == DiagnosticError.LIBRARY_TIMEOUT_ERROR
        assert diagnostics[0].range == Range.zero()

    def test_default_libraries_without_errors_report_nothing(self, mocker: MockerFixture) -> None:
        im = mocker.MagicMock()
        im.get_libdoc_for_library_import_with_meta.side_effect = lambda name, *args, **kwargs: (
            _lib_doc(mocker, name),
            None,
        )

        resolved = _resolve(mocker, im, [])

        assert not [d for d in resolved.diagnostics if "default library" in d.message]


_INIT_ERROR = Error(
    message="Initializing library 'StrictLib' with arguments [ bogus ] failed: ValueError: unknown mode 'bogus'",
    type_name="DataError",
)


def _strict_import(source: str = _SOURCE, line_no: int = 2) -> LibraryImport:
    return LibraryImport(
        line_no=line_no,
        col_offset=0,
        end_line_no=line_no,
        end_col_offset=30,
        source=source,
        name="StrictLib.py",
        name_token=None,
        args=("bogus",),
    )


def _manager(mocker: MockerFixture, strict_doc: Any) -> Any:
    im = mocker.MagicMock()
    im.get_libdoc_for_library_import_with_meta.side_effect = lambda name, *args, **kwargs: (
        strict_doc if name == "StrictLib.py" else _lib_doc(mocker, name),
        None,
    )
    return im


class TestLoadedWithoutArguments:
    def test_marked_document_reports_the_errors_then_the_information(self, mocker: MockerFixture) -> None:
        imp = _strict_import()
        doc = _lib_doc(mocker, "StrictLib", [_INIT_ERROR], loaded_without_arguments=True)
        doc.source = None

        resolved = _resolve(mocker, _manager(mocker, doc), [imp])

        diagnostics = [d for d in resolved.diagnostics if d.range == imp.range]
        assert [(d.code, d.severity) for d in diagnostics] == [
            ("DataError", DiagnosticSeverity.ERROR),
            (DiagnosticError.LIBRARY_LOADED_WITHOUT_ARGUMENTS, DiagnosticSeverity.INFORMATION),
        ]
        assert diagnostics[1].message == (
            "Keywords of library 'StrictLib' come from loading it without arguments, "
            "because loading it with the import's arguments failed."
        )

    def test_unmarked_document_with_errors_reports_no_information(self, mocker: MockerFixture) -> None:
        imp = _strict_import()
        doc = _lib_doc(mocker, "StrictLib", [_INIT_ERROR])

        resolved = _resolve(mocker, _manager(mocker, doc), [imp])

        assert not [d for d in resolved.diagnostics if d.code == DiagnosticError.LIBRARY_LOADED_WITHOUT_ARGUMENTS]

    def test_marked_document_imported_through_a_resource_file_reports_nothing_in_the_suite(
        self, mocker: MockerFixture
    ) -> None:
        resource_source = "/project/common.resource"
        doc = _lib_doc(mocker, "StrictLib", [_INIT_ERROR], loaded_without_arguments=True)
        im = _manager(mocker, doc)
        resource_doc = mocker.MagicMock()
        resource_doc.name = "common"
        resource_doc.source = resource_source
        resource_doc.source_id = None
        resource_doc.resource_imports = [_strict_import(source=resource_source)]
        resource_doc.resource_variables = []
        resource_doc.errors = None
        resource_doc.keywords = [mocker.MagicMock()]
        resource_doc.loaded_without_arguments = False
        im.get_resource_doc_for_resource_import_with_meta.return_value = (resource_doc, None)

        resolved = _resolve(
            mocker,
            im,
            [
                ResourceImport(
                    line_no=2,
                    col_offset=0,
                    end_line_no=2,
                    end_col_offset=30,
                    source=_SOURCE,
                    name="common.resource",
                    name_token=None,
                )
            ],
        )

        assert "StrictLib.py" in [c.args[0] for c in im.get_libdoc_for_library_import_with_meta.call_args_list]
        assert not [d for d in resolved.diagnostics if d.code == DiagnosticError.LIBRARY_LOADED_WITHOUT_ARGUMENTS]
