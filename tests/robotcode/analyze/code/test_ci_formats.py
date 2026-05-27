import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from robotcode.analyze.code.cli import (
    _collect_sorted_diagnostics,
    build_github_annotations,
    build_gitlab_report,
)
from robotcode.analyze.code.code_analyzer import DocumentDiagnosticReport, FolderDiagnosticReport
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range
from robotcode.core.uri import Uri
from robotcode.core.workspace import WorkspaceFolder


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return Uri.from_path(tmp_path).to_path()


def _diag(
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
    code: Any = "KeywordNotFound",
    message: str = "boom",
    line: int = 3,
    character: int = 4,
) -> Diagnostic:
    return Diagnostic(
        range=Range(start=Position(line=line, character=character), end=Position(line=line, character=character + 6)),
        message=message,
        severity=severity,
        code=code,
    )


def _doc_report(path: Path, items: List[Diagnostic]) -> DocumentDiagnosticReport:
    doc: Any = type("Doc", (), {"uri": Uri.from_path(path)})()
    return DocumentDiagnosticReport(document=doc, items=items)


def _folder_report(path: Path, items: List[Diagnostic]) -> FolderDiagnosticReport:
    return FolderDiagnosticReport(folder=WorkspaceFolder(path.name, Uri.from_path(path)), items=items)


def _github(reports: List[Any], root: Path, full_paths: bool = False) -> List[str]:
    folders, docs = _collect_sorted_diagnostics(reports, root, full_paths)
    return build_github_annotations(folders, docs)


def _gitlab(reports: List[Any], root: Path, full_paths: bool = False) -> List[Dict[str, Any]]:
    folders, docs = _collect_sorted_diagnostics(reports, root, full_paths)
    return build_gitlab_report(folders, docs)


class TestGithubAnnotations:
    def test_basic_line_format_one_based(self, root: Path) -> None:
        lines = _github([_doc_report(root / "f.robot", [_diag(line=3, character=4)])], root)

        assert lines == [
            "::error file=f.robot,line=4,endLine=4,col=5,endColumn=11,title=KeywordNotFound::boom",
        ]

    @pytest.mark.parametrize(
        ("severity", "command"),
        [
            (DiagnosticSeverity.ERROR, "error"),
            (DiagnosticSeverity.WARNING, "warning"),
            (DiagnosticSeverity.INFORMATION, "notice"),
            (DiagnosticSeverity.HINT, "notice"),
        ],
    )
    def test_severity_maps_to_command(self, root: Path, severity: DiagnosticSeverity, command: str) -> None:
        lines = _github([_doc_report(root / "f.robot", [_diag(severity=severity)])], root)

        assert lines[0].startswith(f"::{command} ")

    def test_message_escaping(self, root: Path) -> None:
        lines = _github([_doc_report(root / "f.robot", [_diag(message="a\nb%c\rd")])], root)

        # newline -> %0A, percent -> %25, carriage return -> %0D in the message part.
        message_part = lines[0].split("::", 2)[2]
        assert message_part == "a%0Ab%25c%0Dd"

    def test_property_escaping_for_comma_and_colon(self, root: Path) -> None:
        # A code containing ',' and ':' must be escaped in the title property.
        lines = _github([_doc_report(root / "f.robot", [_diag(code="a,b:c")])], root)

        assert "title=a%2Cb%3Ac" in lines[0]

    def test_missing_code_omits_title(self, root: Path) -> None:
        lines = _github([_doc_report(root / "f.robot", [_diag(code=None)])], root)

        assert "title=" not in lines[0]


class TestGitlabReport:
    def test_minimal_entry_shape(self, root: Path) -> None:
        report = _gitlab([_doc_report(root / "sub" / "f.robot", [_diag(line=3)])], root)

        assert len(report) == 1
        entry = report[0]
        assert entry["description"] == "boom"
        assert entry["check_name"] == "KeywordNotFound"
        assert entry["location"] == {"path": "sub/f.robot", "lines": {"begin": 4}}
        assert isinstance(entry["fingerprint"], str)
        assert entry["fingerprint"]

    @pytest.mark.parametrize(
        ("severity", "gitlab_severity"),
        [
            (DiagnosticSeverity.ERROR, "major"),
            (DiagnosticSeverity.WARNING, "minor"),
            (DiagnosticSeverity.INFORMATION, "info"),
            (DiagnosticSeverity.HINT, "info"),
        ],
    )
    def test_severity_maps(self, root: Path, severity: DiagnosticSeverity, gitlab_severity: str) -> None:
        report = _gitlab([_doc_report(root / "f.robot", [_diag(severity=severity)])], root)

        assert report[0]["severity"] == gitlab_severity

    def test_field_names_are_snake_case(self, root: Path) -> None:
        # Round-trip through JSON to be sure the keys are exactly what GitLab expects.
        report = _gitlab([_doc_report(root / "f.robot", [_diag()])], root)
        keys = set(json.loads(json.dumps(report))[0])

        assert keys == {"description", "check_name", "fingerprint", "severity", "location"}

    def test_identical_findings_get_distinct_fingerprints(self, root: Path) -> None:
        report = _gitlab([_doc_report(root / "f.robot", [_diag(line=1), _diag(line=2)])], root)

        assert len({e["fingerprint"] for e in report}) == 2

    def test_missing_code_falls_back_to_robotcode(self, root: Path) -> None:
        report = _gitlab([_doc_report(root / "f.robot", [_diag(code=None)])], root)

        assert report[0]["check_name"] == "robotcode"


class TestFolderDiagnosticsInCiFormats:
    def test_github_folder_diagnostic_uses_dot(self, root: Path) -> None:
        lines = _github([_folder_report(root, [_diag(code="DataError")])], root)

        assert "file=." in lines[0]

    def test_gitlab_folder_diagnostic_uses_dot(self, root: Path) -> None:
        report = _gitlab([_folder_report(root, [_diag(code="DataError")])], root)

        assert report[0]["location"]["path"] == "."
