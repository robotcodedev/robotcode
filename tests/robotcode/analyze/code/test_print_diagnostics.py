from pathlib import Path
from typing import Any, List, Optional, Tuple

import click
import pytest
from pytest_mock import MockerFixture

from robotcode.analyze.code.cli import SEVERITY_COLORS, _print_diagnostics
from robotcode.core.lsp.types import (
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    Location,
    Position,
    Range,
)
from robotcode.core.uri import Uri


def _range(line: int = 0, character: int = 0) -> Range:
    return Range(start=Position(line=line, character=character), end=Position(line=line, character=character))


def _diag(
    severity: Optional[DiagnosticSeverity] = DiagnosticSeverity.ERROR,
    code: str = "Code",
    message: str = "msg",
    line: int = 0,
    character: int = 0,
    related: Optional[List[DiagnosticRelatedInformation]] = None,
) -> Diagnostic:
    return Diagnostic(
        range=_range(line, character),
        message=message,
        severity=severity,
        code=code,
        related_information=related,
    )


def _related(path: Path, line: int = 5, character: int = 2, message: str = "rel") -> DiagnosticRelatedInformation:
    return DiagnosticRelatedInformation(
        location=Location(uri=str(Uri.from_path(path)), range=_range(line, character)),
        message=message,
    )


def _capture(mocker: MockerFixture) -> Tuple[Any, List[str]]:
    """Return (app_mock, echoed_lines)."""
    lines: List[str] = []
    app = mocker.Mock()
    app.echo.side_effect = lambda s: lines.append(s)
    return app, lines


class TestDocumentDiagnostics:
    def test_renders_path_severity_code_and_message(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        doc_path = Path("tests/api/foo.robot")

        _print_diagnostics(
            app,
            tmp_path,
            [_diag(severity=DiagnosticSeverity.ERROR, code="KeywordNotFound", message="boom", line=3, character=4)],
            doc_path,
        )

        assert len(lines) == 1
        line = lines[0]
        assert line.startswith("tests/api/foo.robot:4:5: ")
        # ANSI red, severity label, code, then message.
        assert click.style("[E] KeywordNotFound", fg=SEVERITY_COLORS[DiagnosticSeverity.ERROR]) in line
        assert line.endswith(": boom")

    def test_warning_uses_yellow(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)

        _print_diagnostics(app, tmp_path, [_diag(severity=DiagnosticSeverity.WARNING, code="W")], Path("x.robot"))

        assert click.style("[W] W", fg=SEVERITY_COLORS[DiagnosticSeverity.WARNING]) in lines[0]

    def test_diagnostic_without_severity_falls_back_to_error(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)

        _print_diagnostics(app, tmp_path, [_diag(severity=None, code="X")], Path("y.robot"))

        assert click.style("[E] X", fg=SEVERITY_COLORS[DiagnosticSeverity.ERROR]) in lines[0]


class TestFolderDiagnostics:
    def test_dot_marker_and_no_line_col_when_print_range_false(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)

        _print_diagnostics(
            app,
            tmp_path,
            [_diag(severity=DiagnosticSeverity.ERROR, code="DataError", message="bad")],
            Path("."),
            print_range=False,
        )

        assert len(lines) == 1
        # Top-line has the dot marker, no line:col.
        assert lines[0].startswith(".: ")
        assert "1:1" not in lines[0]

    def test_empty_folder_path_suppresses_prefix(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)

        _print_diagnostics(app, tmp_path, [_diag(code="X")], None)

        # No path prefix at all when folder_path is None: the line starts directly with the styled label.
        assert lines[0].startswith(click.style("[E] X", fg=SEVERITY_COLORS[DiagnosticSeverity.ERROR]))


class TestRelatedInformation:
    def test_related_info_always_shows_line_col_even_when_top_line_does_not(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        app, lines = _capture(mocker)
        related_file = tmp_path / "broken.py"

        _print_diagnostics(
            app,
            tmp_path,
            [
                _diag(
                    severity=DiagnosticSeverity.ERROR,
                    related=[_related(related_file, line=10, character=3, message="bang")],
                )
            ],
            Path("."),
            print_range=False,
        )

        # First line: top-level diagnostic without line:col.
        # Second line: related, always with line:col.
        assert len(lines) == 2
        assert lines[0].startswith(".: ")
        assert "broken.py:11:4: " in lines[1]
        assert lines[1].rstrip().endswith("bang")

    def test_related_path_is_relative_to_root_when_possible(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        related_file = tmp_path / "sub" / "deep.py"
        related_file.parent.mkdir(parents=True)
        related_file.write_text("")

        _print_diagnostics(
            app,
            tmp_path,
            [_diag(related=[_related(related_file, line=0, character=0)])],
            Path("doc.robot"),
        )

        assert "sub/deep.py:1:1:" in lines[1]


class TestSeverityColors:
    @pytest.mark.parametrize(
        ("severity", "label"),
        [
            (DiagnosticSeverity.ERROR, "[E]"),
            (DiagnosticSeverity.WARNING, "[W]"),
            (DiagnosticSeverity.INFORMATION, "[I]"),
            (DiagnosticSeverity.HINT, "[H]"),
        ],
    )
    def test_each_severity_uses_its_color(
        self, mocker: MockerFixture, tmp_path: Path, severity: DiagnosticSeverity, label: str
    ) -> None:
        app, lines = _capture(mocker)

        _print_diagnostics(app, tmp_path, [_diag(severity=severity, code="C")], Path("x.robot"))

        assert click.style(f"{label} C", fg=SEVERITY_COLORS[severity]) in lines[0]
