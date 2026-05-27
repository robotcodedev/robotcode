from typing import Any, List, Optional, Set

import click
import pytest

from robotcode.analyze.code.cli import ResultCollector, ReturnCode, _parse_severities
from robotcode.analyze.code.code_analyzer import DocumentDiagnosticReport
from robotcode.analyze.config import ExitCodeMask
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, Position, Range


def _diag(severity: DiagnosticSeverity) -> Diagnostic:
    return Diagnostic(
        range=Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
        message="x",
        severity=severity,
    )


def _report(severities: List[DiagnosticSeverity]) -> DocumentDiagnosticReport:
    # The collector only inspects `.items` and `.document`; the document
    # identity matters only for de-duplication via the internal set.
    return DocumentDiagnosticReport(document=object(), items=[_diag(s) for s in severities])  # type: ignore[arg-type]


class TestResultCollectorCounts:
    def test_initial_state(self) -> None:
        collector = ResultCollector(ExitCodeMask.NONE)
        assert collector.errors == 0
        assert collector.warnings == 0
        assert collector.infos == 0
        assert collector.hints == 0

    def test_counts_each_severity(self) -> None:
        collector = ResultCollector(ExitCodeMask.NONE)
        collector.add_diagnostics_report(
            _report(
                [
                    DiagnosticSeverity.ERROR,
                    DiagnosticSeverity.ERROR,
                    DiagnosticSeverity.WARNING,
                    DiagnosticSeverity.INFORMATION,
                    DiagnosticSeverity.HINT,
                    DiagnosticSeverity.HINT,
                ]
            )
        )
        assert collector.errors == 2
        assert collector.warnings == 1
        assert collector.infos == 1
        assert collector.hints == 2

    def test_counts_aggregate_across_reports(self) -> None:
        collector = ResultCollector(ExitCodeMask.NONE)
        collector.add_diagnostics_report(_report([DiagnosticSeverity.ERROR]))
        collector.add_diagnostics_report(_report([DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING]))
        assert collector.errors == 2
        assert collector.warnings == 1


class TestReturnCode:
    def test_clean_run_returns_success(self) -> None:
        collector = ResultCollector(ExitCodeMask.NONE)
        assert collector.calculate_return_code() == ReturnCode.SUCCESS

    def test_combines_bits_for_all_severities(self) -> None:
        collector = ResultCollector(ExitCodeMask.NONE)
        collector.add_diagnostics_report(
            _report(
                [
                    DiagnosticSeverity.ERROR,
                    DiagnosticSeverity.WARNING,
                    DiagnosticSeverity.INFORMATION,
                    DiagnosticSeverity.HINT,
                ]
            )
        )
        expected = ReturnCode.ERRORS | ReturnCode.WARNINGS | ReturnCode.INFOS | ReturnCode.HINTS
        assert collector.calculate_return_code() == expected

    def test_mask_suppresses_warnings(self) -> None:
        collector = ResultCollector(ExitCodeMask.WARN)
        collector.add_diagnostics_report(_report([DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING]))
        rc = collector.calculate_return_code()
        assert ReturnCode.ERRORS in rc
        assert ReturnCode.WARNINGS not in rc

    def test_mask_all_silences_every_severity(self) -> None:
        collector = ResultCollector(ExitCodeMask.ALL)
        collector.add_diagnostics_report(
            _report(
                [
                    DiagnosticSeverity.ERROR,
                    DiagnosticSeverity.WARNING,
                    DiagnosticSeverity.INFORMATION,
                    DiagnosticSeverity.HINT,
                ]
            )
        )
        assert collector.calculate_return_code() == ReturnCode.SUCCESS


class TestExitCodeMaskParse:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, ExitCodeMask.NONE),
            ((), ExitCodeMask.NONE),
            (("error",), ExitCodeMask.ERROR),
            (("warn",), ExitCodeMask.WARN),
            (("warning",), ExitCodeMask.WARN),
            (("info",), ExitCodeMask.INFO),
            (("information",), ExitCodeMask.INFO),
            (("hint",), ExitCodeMask.HINT),
            (("all",), ExitCodeMask.ALL),
            (("ERROR",), ExitCodeMask.ERROR),
            (("  warn  ",), ExitCodeMask.WARN),
            (("error", "warn"), ExitCodeMask.ERROR | ExitCodeMask.WARN),
            (("error,warn",), ExitCodeMask.ERROR | ExitCodeMask.WARN),
            (("error, warn , info",), ExitCodeMask.ERROR | ExitCodeMask.WARN | ExitCodeMask.INFO),
            ((",,error,",), ExitCodeMask.ERROR),
        ],
    )
    def test_valid_values(self, value: object, expected: ExitCodeMask) -> None:
        assert ExitCodeMask.parse(value) == expected  # type: ignore[arg-type]

    def test_invalid_value_raises_keyerror(self) -> None:
        with pytest.raises(KeyError, match="bogus"):
            ExitCodeMask.parse(("bogus",))


class TestSeverityFilter:
    def test_no_filter_keeps_everything(self) -> None:
        collector = ResultCollector(ExitCodeMask.NONE, severities=None)
        collector.add_diagnostics_report(
            _report([DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING, DiagnosticSeverity.HINT])
        )
        assert (collector.errors, collector.warnings, collector.hints) == (1, 1, 1)

    def test_filter_drops_other_severities_from_counts(self) -> None:
        collector = ResultCollector(ExitCodeMask.NONE, severities={DiagnosticSeverity.WARNING})
        collector.add_diagnostics_report(
            _report([DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING, DiagnosticSeverity.HINT])
        )
        assert (collector.errors, collector.warnings, collector.infos, collector.hints) == (0, 1, 0, 0)

    def test_filter_affects_the_stored_diagnostics(self) -> None:
        collector = ResultCollector(ExitCodeMask.NONE, severities={DiagnosticSeverity.ERROR})
        collector.add_diagnostics_report(_report([DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING]))
        items = collector.diagnostics[0].items
        assert [d.severity for d in items] == [DiagnosticSeverity.ERROR]

    def test_filter_affects_exit_code(self) -> None:
        # Only warnings are kept, so even though an error exists, the exit code reflects warnings only.
        collector = ResultCollector(ExitCodeMask.NONE, severities={DiagnosticSeverity.WARNING})
        collector.add_diagnostics_report(_report([DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING]))
        rc = collector.calculate_return_code()
        assert ReturnCode.WARNINGS in rc
        assert ReturnCode.ERRORS not in rc


class TestParseSeverities:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ((), None),
            (("error",), {DiagnosticSeverity.ERROR}),
            (("warn",), {DiagnosticSeverity.WARNING}),
            (("warning",), {DiagnosticSeverity.WARNING}),
            (("info",), {DiagnosticSeverity.INFORMATION}),
            (("information",), {DiagnosticSeverity.INFORMATION}),
            (("hint",), {DiagnosticSeverity.HINT}),
            (("ERROR",), {DiagnosticSeverity.ERROR}),
            (("  warn  ",), {DiagnosticSeverity.WARNING}),
            (("error,hint",), {DiagnosticSeverity.ERROR, DiagnosticSeverity.HINT}),
            (("error", "hint"), {DiagnosticSeverity.ERROR, DiagnosticSeverity.HINT}),
            ((",,error,",), {DiagnosticSeverity.ERROR}),
        ],
    )
    def test_valid_values(self, value: Any, expected: Optional[Set[DiagnosticSeverity]]) -> None:
        assert _parse_severities(None, None, value) == expected  # type: ignore[arg-type]

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(click.BadParameter, match="bogus"):
            _parse_severities(None, None, ("bogus",))  # type: ignore[arg-type]


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (0.0, "0.00s"),
            (0.5, "0.50s"),
            (1.234, "1.23s"),
            (59.99, "59.99s"),
            (60.0, "1m 0.00s"),
            (65.5, "1m 5.50s"),
            (3599.99, "59m 59.99s"),
            (3600.0, "1h 0m 0.00s"),
            (3665.5, "1h 1m 5.50s"),
            (-1.0, "0.00s"),
        ],
    )
    def test_format(self, seconds: float, expected: str) -> None:
        assert ResultCollector._format_duration(seconds) == expected
