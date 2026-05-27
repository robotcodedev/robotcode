import json
from pathlib import Path
from typing import Any, List

import pytest

from robotcode.analyze.code._models import CodeAnalysisResult, CodeAnalysisSummary
from robotcode.analyze.code.cli import _build_analysis_result, _collect_sorted_diagnostics
from robotcode.analyze.code.code_analyzer import DocumentDiagnosticReport, FolderDiagnosticReport
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range
from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import as_json
from robotcode.core.workspace import WorkspaceFolder


@pytest.fixture
def root(tmp_path: Path) -> Path:
    # Normalize the root the same way the reports' URIs are (Uri.to_path lower-cases the
    # Windows drive letter), so relative_to is deterministic across platforms.
    return Uri.from_path(tmp_path).to_path()


def _diag(
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    code: str = "KeywordNotFound",
    line: int = 3,
    character: int = 4,
) -> Diagnostic:
    return Diagnostic(
        range=Range(start=Position(line=line, character=character), end=Position(line=line, character=character + 6)),
        message="boom",
        severity=severity,
        code=code,
    )


def _doc_report(path: Path, items: List[Diagnostic]) -> DocumentDiagnosticReport:
    doc: Any = type("Doc", (), {"uri": Uri.from_path(path)})()
    return DocumentDiagnosticReport(document=doc, items=items)


def _folder_report(path: Path, items: List[Diagnostic]) -> FolderDiagnosticReport:
    return FolderDiagnosticReport(folder=WorkspaceFolder(path.name, Uri.from_path(path)), items=items)


class TestCodeAnalysisResultSchema:
    def test_json_shape_is_stable(self) -> None:
        result = CodeAnalysisResult(
            diagnostics={"tests/api/foo.robot": [_diag()]},
            summary=CodeAnalysisSummary(files=1, errors=1, warnings=0, infos=0, hints=0),
        )

        data = json.loads(as_json(result))

        assert set(data) == {"diagnostics", "summary"}
        assert data["summary"] == {"files": 1, "errors": 1, "warnings": 0, "infos": 0, "hints": 0}

        diag = data["diagnostics"]["tests/api/foo.robot"][0]
        # LSP diagnostic shape: severity is the numeric enum value, range nested, code present.
        assert diag["severity"] == DiagnosticSeverity.ERROR.value
        assert diag["code"] == "KeywordNotFound"
        assert diag["range"]["start"] == {"line": 3, "character": 4}
        assert diag["message"] == "boom"

    def test_severity_values_match_lsp(self) -> None:
        result = CodeAnalysisResult(
            diagnostics={
                "a.robot": [_diag(DiagnosticSeverity.ERROR)],
                "b.robot": [_diag(DiagnosticSeverity.WARNING)],
                "c.robot": [_diag(DiagnosticSeverity.INFORMATION)],
                "d.robot": [_diag(DiagnosticSeverity.HINT)],
            }
        )

        data = json.loads(as_json(result))
        severities = {src: items[0]["severity"] for src, items in data["diagnostics"].items()}

        assert severities == {"a.robot": 1, "b.robot": 2, "c.robot": 3, "d.robot": 4}

    def test_json_schema_is_stable_for_a_clean_run(self) -> None:
        # A clean run (no diagnostics, all counts zero) must still emit the full
        # {diagnostics, summary} shape so CI consumers can rely on a fixed schema.
        # `as_json` is what `print_data` uses for JSON output and does not strip
        # defaults, unlike the TOML path.
        result = CodeAnalysisResult(summary=CodeAnalysisSummary(files=3))

        data = json.loads(as_json(result))

        assert data == {
            "diagnostics": {},
            "summary": {"files": 3, "errors": 0, "warnings": 0, "infos": 0, "hints": 0},
        }


class TestCollectSortedDiagnostics:
    def test_documents_sorted_by_line_then_column(self, root: Path) -> None:
        f = root / "foo.robot"
        reports = [
            _doc_report(f, [_diag(line=7, character=1)]),
            _doc_report(f, [_diag(line=4, character=9), _diag(line=4, character=2)]),
        ]

        _, docs = _collect_sorted_diagnostics(reports, root, full_paths=False)

        # Merged per file, then sorted by (line, column).
        positions = [(d.range.start.line, d.range.start.character) for d in next(iter(docs.values()))]
        assert positions == [(4, 2), (4, 9), (7, 1)]

    def test_relative_vs_full_paths(self, root: Path) -> None:
        f = root / "sub" / "foo.robot"
        reports = [_doc_report(f, [_diag()])]

        _, rel = _collect_sorted_diagnostics(reports, root, full_paths=False)
        _, full = _collect_sorted_diagnostics(reports, root, full_paths=True)

        assert next(iter(rel)) == Path("sub/foo.robot")
        assert next(iter(full)) == f

    def test_empty_reports_are_dropped(self, root: Path) -> None:
        reports = [_doc_report(root / "foo.robot", [])]

        folders, docs = _collect_sorted_diagnostics(reports, root, full_paths=False)

        assert folders == []
        assert docs == {}


class TestBuildAnalysisResult:
    def test_folder_entries_key_on_dot(self, root: Path) -> None:
        folders, docs = _collect_sorted_diagnostics(
            [_folder_report(root, [_diag(code="DataError")])], root, full_paths=False
        )

        result = _build_analysis_result(folders, docs, CodeAnalysisSummary())

        assert list(result.diagnostics) == ["."]

    def test_keys_are_posix_even_on_windows_paths(self, root: Path) -> None:
        f = root / "sub" / "foo.robot"
        folders, docs = _collect_sorted_diagnostics([_doc_report(f, [_diag()])], root, full_paths=False)

        result = _build_analysis_result(folders, docs, CodeAnalysisSummary())

        # POSIX separator regardless of host OS.
        assert "sub/foo.robot" in result.diagnostics

    def test_folder_and_document_merged(self, root: Path) -> None:
        f = root / "foo.robot"
        folders, docs = _collect_sorted_diagnostics(
            [_folder_report(root, [_diag(code="DataError")]), _doc_report(f, [_diag()])],
            root,
            full_paths=False,
        )

        result = _build_analysis_result(folders, docs, CodeAnalysisSummary(files=1, errors=2))

        assert set(result.diagnostics) == {".", "foo.robot"}
        assert result.summary.errors == 2
