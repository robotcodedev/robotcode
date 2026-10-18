"""Tests that ImportResolver records the imports that failed.

A created file invalidates only the namespaces with failed imports, and the
periodic file check of the language server looks up again the failed imports
whose file or module was not found.
"""

from pathlib import Path
from typing import Any, Iterator, List, Type

import pytest
from pytest_mock import MockerFixture

from robotcode.core.documents_manager import DocumentsManager
from robotcode.robot.diagnostics.entities import Import, LibraryImport, ResourceImport, VariablesImport
from robotcode.robot.diagnostics.import_resolver import FailedImport, ImportResolver, ResolvedImports
from robotcode.robot.diagnostics.imports_manager import ImportsManager
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.diagnostics.namespace_analyzer import _get_builtin_variables
from robotcode.robot.diagnostics.variable_scope import VariableScope


@pytest.fixture
def imports_manager(tmp_path: Path, mocker: MockerFixture) -> Iterator[ImportsManager]:
    document_cache_helper = mocker.MagicMock()
    document_cache_helper.get_languages_for_document.return_value = None
    manager = ImportsManager(
        DocumentsManager(), None, document_cache_helper, tmp_path, {}, [], None, [], [], [], [], tmp_path
    )
    yield manager

    manager.data_cache.close()


class _Sentinel:
    """Stands in for a namespace: the import entries live while it is referenced."""


def _import(import_type: Type[Import], suite: Path, name: str) -> Any:
    return import_type(
        line_no=2, col_offset=0, end_line_no=2, end_col_offset=40, source=str(suite), name=name, name_token=None
    )


def _resolve(imports_manager: ImportsManager, suite: Path, imports: List[Any]) -> ResolvedImports:
    scope = VariableScope(
        command_line=imports_manager.get_command_line_variables(),
        builtin=_get_builtin_variables(),
    )
    return ImportResolver(imports_manager, str(suite), scope, sentinel=_Sentinel()).resolve(imports)


@pytest.mark.parametrize(
    ("import_type", "name"),
    [
        pytest.param(ResourceImport, "missing.resource", id="resource file"),
        pytest.param(LibraryImport, "missing_lib.py", id="library file"),
        pytest.param(VariablesImport, "missing_vars.py", id="variable file"),
        pytest.param(LibraryImport, "missing_module", id="library module"),
    ],
)
def test_a_missing_import_counts_as_failed_and_not_found(
    imports_manager: ImportsManager, tmp_path: Path, import_type: Type[Import], name: str
) -> None:
    suite = tmp_path / "suite.robot"
    imp = _import(import_type, suite, name)

    resolved = _resolve(imports_manager, suite, [imp])

    assert [(f.imp, f.base_dir, f.found) for f in resolved.failed_imports] == [(imp, str(tmp_path), False)]


def test_a_library_that_fails_to_load_counts_as_failed_but_found(
    imports_manager: ImportsManager, tmp_path: Path
) -> None:
    (tmp_path / "broken_lib.py").write_text("raise ImportError('a package it needs is missing')\n", encoding="utf-8")
    suite = tmp_path / "suite.robot"
    imp = _import(LibraryImport, suite, "broken_lib.py")

    resolved = _resolve(imports_manager, suite, [imp])

    assert [(f.imp, f.found) for f in resolved.failed_imports] == [(imp, True)]


def test_resolved_imports_do_not_count(imports_manager: ImportsManager, tmp_path: Path) -> None:
    (tmp_path / "vars.py").write_text("X = 1\n", encoding="utf-8")
    suite = tmp_path / "suite.robot"

    resolved = _resolve(
        imports_manager,
        suite,
        [_import(LibraryImport, suite, "Collections"), _import(VariablesImport, suite, "vars.py")],
    )

    assert resolved.failed_imports == []


def test_a_created_file_invalidates_only_a_namespace_with_failed_imports(mocker: MockerFixture, tmp_path: Path) -> None:
    namespace = mocker.MagicMock()
    namespace._failed_imports = []

    Namespace._on_imports_changed(namespace, None, "file:///created.robot")

    namespace.invalidated.assert_not_called()

    namespace._failed_imports = [
        FailedImport(_import(ResourceImport, tmp_path / "suite.robot", "created.robot"), str(tmp_path), {}, False)
    ]

    Namespace._on_imports_changed(namespace, None, "file:///created.robot")

    namespace.invalidated.assert_called_once_with(namespace)
