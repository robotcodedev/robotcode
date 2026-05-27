from pathlib import Path
from typing import Any, List, Optional, Tuple

import click
import pytest
from pytest_mock import MockerFixture

from robotcode.analyze.code.cli import (
    SEVERITY_COLORS,
    SEVERITY_NAMES,
    _normalize_indent,
    _print_diagnostics,
    _trim_debug_sections,
)
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


def _label(severity: DiagnosticSeverity, code: str) -> str:
    return click.style(f"[{SEVERITY_NAMES[severity]}] {code}", fg=SEVERITY_COLORS[severity])


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
        # Path is rendered with the native separator (backslash on Windows).
        assert line.startswith(f"{doc_path}:4:5: ")
        # ANSI red, severity label, code, then message.
        assert _label(DiagnosticSeverity.ERROR, "KeywordNotFound") in line
        assert line.endswith(": boom")

    def test_warning_uses_yellow(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)

        _print_diagnostics(app, tmp_path, [_diag(severity=DiagnosticSeverity.WARNING, code="W")], Path("x.robot"))

        assert _label(DiagnosticSeverity.WARNING, "W") in lines[0]

    def test_diagnostic_without_severity_falls_back_to_error(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)

        _print_diagnostics(app, tmp_path, [_diag(severity=None, code="X")], Path("y.robot"))

        assert _label(DiagnosticSeverity.ERROR, "X") in lines[0]


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
        assert lines[0].startswith(_label(DiagnosticSeverity.ERROR, "X"))


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

        assert f"{Path('sub/deep.py')}:1:1:" in lines[1]

    def test_related_message_trimmed_by_default(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        related_file = tmp_path / "x.py"
        multi = "headline\nTraceback (most recent call last):\n  None\nPYTHONPATH:\n  /a"

        _print_diagnostics(
            app,
            tmp_path,
            [_diag(related=[_related(related_file, message=multi)])],
            Path("doc.robot"),
        )

        assert "headline" in lines[1]
        assert "Traceback" not in lines[1]
        assert "PYTHONPATH" not in lines[1]

    def test_related_line_has_arrow_marker(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        related_file = tmp_path / "x.py"

        _print_diagnostics(
            app,
            tmp_path,
            [_diag(related=[_related(related_file, message="something")])],
            Path("doc.robot"),
        )

        # Marker `-> ` makes related lines visually distinct from regular diagnostics.
        assert lines[1].startswith("    -> ")

    def test_empty_related_message_gets_fallback(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        related_file = tmp_path / "x.py"

        _print_diagnostics(
            app,
            tmp_path,
            [_diag(related=[_related(related_file, message="")])],
            Path("doc.robot"),
        )

        assert "(see related location)" in lines[1]

    def test_related_message_full_when_show_tracebacks(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        related_file = tmp_path / "x.py"
        multi = "headline\nTraceback (most recent call last):\n  None"

        _print_diagnostics(
            app,
            tmp_path,
            [_diag(related=[_related(related_file, message=multi)])],
            Path("doc.robot"),
            show_tracebacks=True,
        )

        assert "headline" in lines[1]
        assert "Traceback" in lines[1]


class TestTrimDebugSections:
    def test_keeps_message_without_markers_unchanged(self) -> None:
        msg = "Multiple keywords matching name 'x' found:\n  alt one\n  alt two"
        assert _trim_debug_sections(msg) == msg

    def test_drops_python_traceback(self) -> None:
        msg = "headline\nTraceback (most recent call last):\n  None"
        assert _trim_debug_sections(msg) == "headline"

    def test_drops_pythonpath_block(self) -> None:
        msg = "headline\nPYTHONPATH:\n  /a\n  /b"
        assert _trim_debug_sections(msg) == "headline"

    def test_drops_indented_markers(self) -> None:
        # Markers can appear indented (as Robot's error.message sometimes wraps them).
        msg = "headline\n    Traceback (most recent call last):\n      None"
        assert _trim_debug_sections(msg) == "headline"

    def test_item_message_drops_traceback_by_default(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        long_msg = "Importing test library 'X' failed: ModuleNotFoundError\nTraceback (most recent call last):\n  None"

        _print_diagnostics(app, tmp_path, [_diag(message=long_msg, code="DataError")], Path("doc.robot"))

        assert "Importing test library" in lines[0]
        assert "Traceback" not in lines[0]

    def test_item_message_full_when_show_tracebacks(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        long_msg = "Importing test library 'X' failed: ModuleNotFoundError\nTraceback (most recent call last):\n  None"

        _print_diagnostics(
            app, tmp_path, [_diag(message=long_msg, code="DataError")], Path("doc.robot"), show_tracebacks=True
        )

        assert "Importing test library" in lines[0]
        assert "Traceback" in lines[0]


class TestNormalizeIndent:
    def test_single_line_passes_through(self) -> None:
        assert _normalize_indent("just one line", "    ") == "just one line"

    def test_multiline_reindents_subsequent_lines(self) -> None:
        msg = "headline:\n      alt one\n      alt two"
        assert _normalize_indent(msg, "    ") == "headline:\n    alt one\n    alt two"

    def test_blank_lines_dropped(self) -> None:
        msg = "headline:\n\n  alt\n   \n  alt2"
        assert _normalize_indent(msg, "    ") == "headline:\n    alt\n    alt2"

    def test_first_line_is_stripped(self) -> None:
        assert _normalize_indent("   leading\n  child", "    ") == "leading\n    child"

    def test_empty_input(self) -> None:
        assert _normalize_indent("", "    ") == ""


class TestMultiLineItemMessage:
    def test_multiline_item_message_is_reindented(self, mocker: MockerFixture, tmp_path: Path) -> None:
        app, lines = _capture(mocker)
        msg = "Multiple keywords found:\n        alt one\n        alt two"

        _print_diagnostics(app, tmp_path, [_diag(message=msg, code="MultipleKeywords")], Path("doc.robot"))

        # Single echo call carrying multi-line content.
        assert len(lines) == 1
        out_lines = lines[0].split("\n")
        assert out_lines[0].endswith(": Multiple keywords found:")
        assert out_lines[1] == "    alt one"
        assert out_lines[2] == "    alt two"


class TestSeverityColors:
    @pytest.mark.parametrize(
        "severity",
        [
            DiagnosticSeverity.ERROR,
            DiagnosticSeverity.WARNING,
            DiagnosticSeverity.INFORMATION,
            DiagnosticSeverity.HINT,
        ],
    )
    def test_each_severity_uses_its_color(
        self, mocker: MockerFixture, tmp_path: Path, severity: DiagnosticSeverity
    ) -> None:
        app, lines = _capture(mocker)

        _print_diagnostics(app, tmp_path, [_diag(severity=severity, code="C")], Path("x.robot"))

        assert _label(severity, "C") in lines[0]
