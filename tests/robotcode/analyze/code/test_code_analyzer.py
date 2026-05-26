from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, cast

import pytest
from pytest_mock import MockerFixture

from robotcode.analyze.code.code_analyzer import (
    CodeAnalyzer,
    DocumentDiagnosticReport,
    FolderDiagnosticReport,
)
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range


@pytest.fixture
def file_tree(tmp_path: Path) -> Dict[str, Path]:
    """
    Build:
        <tmp>/tests/api/foo.robot
        <tmp>/tests/api_v2/bar.robot
        <tmp>/tests/other/baz.robot
    """
    api = tmp_path / "tests" / "api"
    api_v2 = tmp_path / "tests" / "api_v2"
    other = tmp_path / "tests" / "other"
    for d in (api, api_v2, other):
        d.mkdir(parents=True)

    foo = api / "foo.robot"
    bar = api_v2 / "bar.robot"
    baz = other / "baz.robot"
    for f in (foo, bar, baz):
        f.write_text("*** Test Cases ***\nT\n    Log    x\n")

    return {"root": tmp_path, "api": api, "api_v2": api_v2, "foo": foo, "bar": bar, "baz": baz}


def _build_analyzer(mocker: MockerFixture, root: Path, files: List[Path]) -> CodeAnalyzer:
    """Build a minimal CodeAnalyzer that only has what collect_documents needs."""
    analyzer: Any = object.__new__(CodeAnalyzer)
    analyzer.app = mocker.Mock()

    def make_doc(path: Path) -> Any:
        doc = mocker.Mock()
        doc.uri.to_path.return_value = path
        return doc

    workspace = mocker.Mock()
    workspace.documents.get_or_open_document.side_effect = make_doc
    analyzer._workspace = workspace

    handler = mocker.Mock()
    handler.collect_workspace_folder_files.return_value = files
    analyzer.language_handlers = [handler]

    return cast(CodeAnalyzer, analyzer)


def _doc_paths(documents: List[Any]) -> List[Path]:
    return [d.uri.to_path() for d in documents]


class TestCollectDocumentsPathFilter:
    def test_no_paths_returns_all_files(self, mocker: MockerFixture, file_tree: Dict[str, Path]) -> None:
        analyzer = _build_analyzer(mocker, file_tree["root"], [file_tree["foo"], file_tree["bar"], file_tree["baz"]])
        folder = mocker.Mock()
        folder.uri.to_path.return_value = file_tree["root"]

        docs = analyzer.collect_documents(folder)

        assert sorted(_doc_paths(docs)) == sorted([file_tree["foo"], file_tree["bar"], file_tree["baz"]])

    def test_directory_filter_excludes_sibling_with_shared_prefix(
        self, mocker: MockerFixture, file_tree: Dict[str, Path]
    ) -> None:
        # Regression test: passing `tests/api` must not pull in `tests/api_v2/bar.robot`.
        analyzer = _build_analyzer(mocker, file_tree["root"], [file_tree["foo"], file_tree["bar"], file_tree["baz"]])
        folder = mocker.Mock()
        folder.uri.to_path.return_value = file_tree["root"]

        docs = analyzer.collect_documents(folder, paths=[file_tree["api"]])

        assert _doc_paths(docs) == [file_tree["foo"]]

    def test_multiple_path_filters_are_unioned(self, mocker: MockerFixture, file_tree: Dict[str, Path]) -> None:
        analyzer = _build_analyzer(mocker, file_tree["root"], [file_tree["foo"], file_tree["bar"], file_tree["baz"]])
        folder = mocker.Mock()
        folder.uri.to_path.return_value = file_tree["root"]

        docs = analyzer.collect_documents(folder, paths=[file_tree["api"], file_tree["api_v2"]])

        assert sorted(_doc_paths(docs)) == sorted([file_tree["foo"], file_tree["bar"]])

    def test_single_file_filter_matches_only_that_file(self, mocker: MockerFixture, file_tree: Dict[str, Path]) -> None:
        analyzer = _build_analyzer(mocker, file_tree["root"], [file_tree["foo"], file_tree["bar"], file_tree["baz"]])
        folder = mocker.Mock()
        folder.uri.to_path.return_value = file_tree["root"]

        docs = analyzer.collect_documents(folder, paths=[file_tree["foo"]])

        assert _doc_paths(docs) == [file_tree["foo"]]


def _diag(severity: DiagnosticSeverity = DiagnosticSeverity.ERROR, message: str = "x") -> Diagnostic:
    return Diagnostic(
        range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
        message=message,
        severity=severity,
    )


@contextmanager
def _passthrough_progressbar(items: Iterable[Any], label: str = "") -> Any:
    yield iter(list(items))


def _build_run_analyzer(
    mocker: MockerFixture,
    documents: List[Any],
    folder_result: Any = None,
    analyze_result: Any = None,
    collect_result: Any = None,
) -> CodeAnalyzer:
    """
    Build a CodeAnalyzer wired up just enough for `run()`.

    *_result values follow the DiagnosticHandlers contract: a list whose entries
    are List[Diagnostic], BaseException, or None; or None to skip the phase.
    """
    analyzer: Any = object.__new__(CodeAnalyzer)

    app = mocker.Mock()
    app.progressbar.side_effect = _passthrough_progressbar
    analyzer.app = app

    folder = mocker.Mock()
    folder.uri.to_path.return_value = Path("/ws")

    workspace = mocker.Mock()
    workspace.workspace_folders = [folder]
    analyzer._workspace = workspace

    diagnostics_handlers = mocker.Mock()
    diagnostics_handlers.analyze_folder.return_value = folder_result
    diagnostics_handlers.analyze_document.return_value = analyze_result
    diagnostics_handlers.collect_diagnostics.return_value = collect_result
    analyzer._dispatcher = diagnostics_handlers

    mocker.patch.object(CodeAnalyzer, "collect_documents", return_value=documents)

    return cast(CodeAnalyzer, analyzer)


class TestRunYields:
    def test_pass1_skips_empty_document_reports(self, mocker: MockerFixture) -> None:
        # analyze_document returns [None] (no diagnostics) -> Pass 1 must not yield.
        # collect_diagnostics also returns [None] -> Pass 2 still yields (empty), for file counting.
        doc = mocker.Mock()
        analyzer = _build_run_analyzer(
            mocker,
            documents=[doc],
            analyze_result=[None],
            collect_result=[None],
        )

        reports = list(analyzer.run())

        doc_reports = [r for r in reports if isinstance(r, DocumentDiagnosticReport)]
        assert len(doc_reports) == 1
        assert doc_reports[0].items == []

    def test_pass1_yields_when_provider_returns_diagnostics(self, mocker: MockerFixture) -> None:
        # Pass 1 returns diagnostics -> it must yield. Pass 2 still yields (empty).
        doc = mocker.Mock()
        d = _diag(DiagnosticSeverity.WARNING)
        analyzer = _build_run_analyzer(
            mocker,
            documents=[doc],
            analyze_result=[[d]],
            collect_result=[None],
        )

        doc_reports = [r for r in analyzer.run() if isinstance(r, DocumentDiagnosticReport)]
        # Two reports: one from Pass 1 (with the warning), one from Pass 2 (empty for counting).
        assert len(doc_reports) == 2
        assert doc_reports[0].items == [d]
        assert doc_reports[1].items == []

    def test_both_passes_yield_when_both_return_diagnostics(self, mocker: MockerFixture) -> None:
        doc = mocker.Mock()
        warn = _diag(DiagnosticSeverity.WARNING, message="w")
        err = _diag(DiagnosticSeverity.ERROR, message="e")
        analyzer = _build_run_analyzer(
            mocker,
            documents=[doc],
            analyze_result=[[warn]],
            collect_result=[[err]],
        )

        doc_reports = [r for r in analyzer.run() if isinstance(r, DocumentDiagnosticReport)]
        assert len(doc_reports) == 2
        assert doc_reports[0].items == [warn]
        assert doc_reports[1].items == [err]

    def test_pass2_always_yields_for_file_counting(self, mocker: MockerFixture) -> None:
        # Pass 2 must yield even when there are no diagnostics, otherwise the
        # `Files: N` statistic underreports.
        doc = mocker.Mock()
        analyzer = _build_run_analyzer(
            mocker,
            documents=[doc],
            analyze_result=None,
            collect_result=[None],
        )

        doc_reports = [r for r in analyzer.run() if isinstance(r, DocumentDiagnosticReport)]
        assert len(doc_reports) == 1
        assert doc_reports[0].document is doc

    def test_folder_diagnostics_yielded_as_folder_report(self, mocker: MockerFixture) -> None:
        d = _diag()
        analyzer = _build_run_analyzer(
            mocker,
            documents=[],
            folder_result=[[d]],
        )

        reports = list(analyzer.run())

        folder_reports = [r for r in reports if isinstance(r, FolderDiagnosticReport)]
        assert len(folder_reports) == 1
        assert folder_reports[0].items == [d]

    def test_folder_analyzer_exception_routes_to_app_error(self, mocker: MockerFixture) -> None:
        boom = RuntimeError("kaboom")
        analyzer = _build_run_analyzer(
            mocker,
            documents=[],
            folder_result=[boom],
        )

        reports = list(analyzer.run())

        app_error = cast(Any, analyzer.app).error
        app_error.assert_called_once()
        assert "kaboom" in app_error.call_args[0][0]
        # Still yields the folder report (with no items, since the exception was swallowed).
        folder_reports = [r for r in reports if isinstance(r, FolderDiagnosticReport)]
        assert len(folder_reports) == 1
        assert folder_reports[0].items == []

    def test_folder_analyzer_returns_none_skips_folder_report(self, mocker: MockerFixture) -> None:
        analyzer = _build_run_analyzer(
            mocker,
            documents=[],
            folder_result=None,
        )

        reports = list(analyzer.run())

        assert not any(isinstance(r, FolderDiagnosticReport) for r in reports)
