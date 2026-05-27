import json
from pathlib import Path
from typing import Any, Dict, List

import click
import pytest
from pytest_mock import MockerFixture

from robotcode.analyze.code._sarif import SARIF_SCHEMA, SARIF_VERSION
from robotcode.analyze.code.cli import _collect_sorted_diagnostics, _write_or_echo, build_sarif_log
from robotcode.analyze.code.code_analyzer import DocumentDiagnosticReport, FolderDiagnosticReport
from robotcode.core.lsp.types import (
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    Location,
    Position,
    Range,
)
from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import as_json
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
    related: Any = None,
) -> Diagnostic:
    return Diagnostic(
        range=Range(start=Position(line=line, character=character), end=Position(line=line, character=character + 6)),
        message=message,
        severity=severity,
        code=code,
        related_information=related,
    )


def _doc_report(path: Path, items: List[Diagnostic]) -> DocumentDiagnosticReport:
    doc: Any = type("Doc", (), {"uri": Uri.from_path(path)})()
    return DocumentDiagnosticReport(document=doc, items=items)


def _folder_report(path: Path, items: List[Diagnostic]) -> FolderDiagnosticReport:
    return FolderDiagnosticReport(folder=WorkspaceFolder(path.name, Uri.from_path(path)), items=items)


def _sarif_dict(reports: List[Any], root: Path, full_paths: bool = False) -> Dict[str, Any]:
    folders, documents = _collect_sorted_diagnostics(reports, root, full_paths)
    log = build_sarif_log(folders, documents, root, full_paths, "9.9.9")
    return json.loads(as_json(log))  # type: ignore[no-any-return]


def _results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(data["runs"][0]["results"])


class TestSarifEnvelope:
    def test_schema_and_version(self, root: Path) -> None:
        data = _sarif_dict([_doc_report(root / "f.robot", [_diag()])], root)

        assert data["$schema"] == SARIF_SCHEMA
        assert data["version"] == SARIF_VERSION
        assert data["runs"][0]["tool"]["driver"]["name"] == "RobotCode"
        assert data["runs"][0]["tool"]["driver"]["version"] == "9.9.9"

    def test_rules_emitted_for_occurring_codes_only(self, root: Path) -> None:
        reports = [
            _doc_report(root / "a.robot", [_diag(code="KeywordNotFound")]),
            _doc_report(root / "b.robot", [_diag(code="VariableNotFound"), _diag(code="KeywordNotFound")]),
        ]
        data = _sarif_dict(reports, root)

        rule_ids = [r["id"] for r in data["runs"][0]["tool"]["driver"]["rules"]]
        # Each code once, in first-seen order (a.robot before b.robot after sorting).
        assert rule_ids == ["KeywordNotFound", "VariableNotFound"]

    def test_rule_index_points_at_correct_rule(self, root: Path) -> None:
        reports = [_doc_report(root / "a.robot", [_diag(code="KeywordNotFound"), _diag(code="VariableNotFound")])]
        data = _sarif_dict(reports, root)

        rules = data["runs"][0]["tool"]["driver"]["rules"]
        for result in _results(data):
            assert rules[result["ruleIndex"]]["id"] == result["ruleId"]


class TestSarifMapping:
    def test_region_is_one_based(self, root: Path) -> None:
        # LSP 0-based (line=3, character=4) -> SARIF 1-based (startLine=4, startColumn=5).
        data = _sarif_dict([_doc_report(root / "f.robot", [_diag(line=3, character=4)])], root)

        region = _results(data)[0]["locations"][0]["physicalLocation"]["region"]
        assert region == {"startLine": 4, "startColumn": 5, "endLine": 4, "endColumn": 11}

    @pytest.mark.parametrize(
        ("severity", "level"),
        [
            (DiagnosticSeverity.ERROR, "error"),
            (DiagnosticSeverity.WARNING, "warning"),
            (DiagnosticSeverity.INFORMATION, "note"),
            (DiagnosticSeverity.HINT, "note"),
        ],
    )
    def test_severity_maps_to_level(self, root: Path, severity: DiagnosticSeverity, level: str) -> None:
        data = _sarif_dict([_doc_report(root / "f.robot", [_diag(severity=severity)])], root)

        assert _results(data)[0]["level"] == level

    def test_uri_is_relative_posix_by_default(self, root: Path) -> None:
        data = _sarif_dict([_doc_report(root / "sub" / "f.robot", [_diag()])], root)

        uri = _results(data)[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        assert uri == "sub/f.robot"

    def test_uri_is_absolute_with_full_paths(self, root: Path) -> None:
        f = root / "sub" / "f.robot"
        data = _sarif_dict([_doc_report(f, [_diag()])], root, full_paths=True)

        uri = _results(data)[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        assert uri == f.as_posix()

    def test_missing_code_falls_back_to_robotcode(self, root: Path) -> None:
        data = _sarif_dict([_doc_report(root / "f.robot", [_diag(code=None)])], root)

        assert _results(data)[0]["ruleId"] == "robotcode"

    def test_related_information_maps_to_related_locations(self, root: Path) -> None:
        related = [
            DiagnosticRelatedInformation(
                location=Location(
                    uri=str(Uri.from_path(root / "other.py")),
                    range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
                ),
                message="see here",
            )
        ]
        data = _sarif_dict([_doc_report(root / "f.robot", [_diag(related=related)])], root)

        rel = _results(data)[0]["relatedLocations"][0]
        assert rel["physicalLocation"]["artifactLocation"]["uri"] == "other.py"
        assert rel["physicalLocation"]["region"]["startLine"] == 1
        assert rel["message"]["text"] == "see here"


class TestSarifFolderDiagnostics:
    def test_folder_diagnostics_key_on_dot(self, root: Path) -> None:
        data = _sarif_dict([_folder_report(root, [_diag(code="DataError")])], root)

        uri = _results(data)[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        assert uri == "."


class TestSarifFingerprints:
    def test_fingerprint_present_and_stable_across_line_shifts(self, root: Path) -> None:
        # Same finding at different lines must yield the same fingerprint (line not hashed).
        a = _sarif_dict([_doc_report(root / "f.robot", [_diag(line=3)])], root)
        b = _sarif_dict([_doc_report(root / "f.robot", [_diag(line=99)])], root)

        fp_a = _results(a)[0]["partialFingerprints"]["robotcode/v1"]
        fp_b = _results(b)[0]["partialFingerprints"]["robotcode/v1"]
        assert fp_a == fp_b

    def test_identical_findings_in_same_file_get_distinct_fingerprints(self, root: Path) -> None:
        data = _sarif_dict([_doc_report(root / "f.robot", [_diag(line=1), _diag(line=2)])], root)

        fps = [r["partialFingerprints"]["robotcode/v1"] for r in _results(data)]
        assert len(set(fps)) == 2


class TestWriteOrEcho:
    def test_writes_to_existing_directory(self, mocker: MockerFixture, tmp_path: Path) -> None:
        target = tmp_path / "out.sarif"

        _write_or_echo(mocker.Mock(), "content", target)

        assert target.read_text() == "content\n"

    def test_overwrites_existing_file(self, mocker: MockerFixture, tmp_path: Path) -> None:
        target = tmp_path / "out.sarif"
        target.write_text("old data that is longer than the new one")

        _write_or_echo(mocker.Mock(), "new", target)

        assert target.read_text() == "new\n"

    def test_missing_parent_directory_raises_usage_error(self, mocker: MockerFixture, tmp_path: Path) -> None:
        target = tmp_path / "does-not-exist" / "out.sarif"

        with pytest.raises(click.UsageError, match="does not exist"):
            _write_or_echo(mocker.Mock(), "content", target)

    def test_none_path_echoes(self, mocker: MockerFixture) -> None:
        app = mocker.Mock()

        _write_or_echo(app, "content", None)

        app.echo.assert_called_once_with("content")
