"""Acceptance tests for messages of several lines in `robotcode results`."""

from pathlib import Path

from ._helpers import find_test, strip_ansi
from .conftest import CliRunner, JsonRunner

_LINES = ["The order total does not match", "Expected 42.00, but got 41.90.", "Check how the tax gets rounded"]
_QUOTE = "\n".join(f"  > {line}" for line in _LINES)
_LONG_LINES = [f"Line {i:02d}: the order total check failed at this step" for i in range(1, 11)]


def test_show_quotes_every_line_of_a_message(text_result: CliRunner, multiline_current_output: Path) -> None:
    plain = strip_ansi(text_result("show", "--failed", output_path=multiline_current_output).stdout)
    assert _QUOTE in plain


def test_summary_quotes_every_line_of_a_failure(text_result: CliRunner, multiline_current_output: Path) -> None:
    plain = strip_ansi(text_result("summary", "--failed", output_path=multiline_current_output).stdout)
    assert _QUOTE in plain


def test_diff_quotes_every_line_of_a_new_failure(
    robotcode_cli: CliRunner, multiline_baseline_output: Path, multiline_current_output: Path
) -> None:
    result = robotcode_cli(["results", "diff", str(multiline_baseline_output), str(multiline_current_output)])
    assert _QUOTE in strip_ansi(result.stdout)


def test_compare_puts_the_lines_of_a_failure_into_one_cell(
    robotcode_cli: CliRunner, multiline_baseline_output: Path, multiline_current_output: Path
) -> None:
    result = robotcode_cli(
        ["results", "compare", "--show", "failures", str(multiline_baseline_output), str(multiline_current_output)]
    )
    rows = [line for line in strip_ansi(result.stdout).splitlines() if line.startswith(f"| {_LINES[0]}")]
    assert len(rows) == 1
    assert rows[0].startswith(f"| {' '.join(_LINES)} ")


def test_message_chars_keeps_whole_lines(json_result: JsonRunner, multiline_current_output: Path) -> None:
    data = json_result("show", "--failed", "--message-chars", "70", output_path=multiline_current_output)
    test = find_test(data["tests"], "Multiline.Order Total")
    assert test is not None
    # Two lines of 30 characters and the line break between them fit into 70, the third line doesn't.
    assert test["message"] == f"{_LINES[0]}\n{_LINES[1]}\n... (1 more line)"
    assert test["fullMessage"] == "\n".join(_LINES)


def test_a_first_line_longer_than_the_limit_is_cut(json_result: JsonRunner, multiline_current_output: Path) -> None:
    data = json_result("show", "--failed", "--message-chars", "20", output_path=multiline_current_output)
    test = find_test(data["tests"], "Multiline.Order Total")
    assert test is not None
    assert test["message"] == "The order total does...\n... (2 more lines)"


def test_summary_shortens_a_message_of_ten_lines_by_default(
    text_result: CliRunner, multiline_long_output: Path
) -> None:
    plain = strip_ansi(text_result("summary", "--failed", output_path=multiline_long_output).stdout)
    assert "\n".join(f"  > {line}" for line in [*_LONG_LINES[:2], "... (8 more lines)"]) in plain
    assert _LONG_LINES[2] not in plain


def test_message_chars_0_keeps_the_whole_message(json_result: JsonRunner, multiline_long_output: Path) -> None:
    data = json_result("show", "--failed", "--message-chars", "0", output_path=multiline_long_output)
    test = find_test(data["tests"], "Multiline.Order Total")
    assert test is not None
    assert test["message"] == "\n".join(_LONG_LINES)
