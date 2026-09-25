"""Acceptance tests for `robotcode results` error-handling paths.

These all assert that a misuse (bad flag, missing file, unparseable
regex, wrong format) is reported as a non-zero exit code with a useful
message on stderr — not a stack trace and not a silent zero.
"""

import json
from pathlib import Path

import pytest

from robotcode.robot.utils import RF_VERSION

from ..rf_markers import needs_rf_75
from .conftest import STATIC_DIR, CliRunner, JsonRunner

# Result files written by Robot Framework 7.5 with a `[Metadata]` setting on
# the test `With Metadata`.
_TEST_METADATA_XML = STATIC_DIR / "rf75_test_metadata.xml"
_TEST_METADATA_JSON = STATIC_DIR / "rf75_test_metadata.json"

_TEST_METADATA_HINT = (
    "The file was written by Robot Framework 7.5 or newer and contains test metadata; "
    "reading it requires Robot Framework 7.5+."
)


def test_missing_output_file_is_a_clear_error(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    """`--output /nonexistent.xml` reports the missing file by path."""
    missing = tmp_path / "no_such.xml"
    result = robotcode_cli(
        ["results", "summary", "--output", str(missing)],
        expect_ok=False,
    )
    assert result.returncode != 0
    combined = (result.stderr + result.stdout).lower()
    assert "not found" in combined or "no such" in combined


def test_output_dir_without_xml_reports_no_result_file(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    """Pointing `--output` at an empty directory yields a discovery error."""
    empty_dir = tmp_path / "empty_results_dir"
    empty_dir.mkdir()
    result = robotcode_cli(
        ["results", "summary", "--output", str(empty_dir)],
        expect_ok=False,
    )
    assert result.returncode != 0
    combined = (result.stderr + result.stdout).lower()
    # Error wording: either "no result file" (auto-discovery) or just "not found"
    assert "result file" in combined or "no " in combined


def test_unknown_global_format_is_rejected(robotcode_cli: CliRunner, basic_output: Path) -> None:
    """`-f bogus` is a Click-level rejection of an enum value."""
    result = robotcode_cli(
        ["--format", "bogus", "results", "summary", "--output", str(basic_output)],
        expect_ok=False,
    )
    assert result.returncode != 0
    # Click's invalid-choice error mentions either the offending value or 'invalid'
    assert b"bogus" in result.stderr.lower().encode() or "invalid" in result.stderr.lower()


def test_unknown_subcommand_is_rejected(robotcode_cli: CliRunner) -> None:
    """Click rejects an unknown subcommand of `results`."""
    result = robotcode_cli(
        ["results", "does-not-exist"],
        expect_ok=False,
    )
    assert result.returncode != 0
    assert "no such" in result.stderr.lower() or "usage" in result.stderr.lower()


@pytest.mark.parametrize("subcommand", ["summary", "show", "log", "stats"])
def test_invalid_search_regex_is_rejected_uniformly(
    subcommand: str, robotcode_cli: CliRunner, basic_output: Path
) -> None:
    """Every search-aware subcommand rejects an unparseable regex."""
    result = robotcode_cli(
        ["results", subcommand, "--search-regex", "[abc", "--output", str(basic_output)],
        expect_ok=False,
    )
    assert result.returncode != 0
    assert "search-regex" in result.stderr.lower() or "invalid" in result.stderr.lower()


# ---------------------------------------------------------------------------
# JSON result files on Robot Framework older than 7.0
# ---------------------------------------------------------------------------


@pytest.mark.skipif(RF_VERSION >= (7, 0), reason="Robot Framework 7.0+ reads JSON result files")
def test_json_on_old_robot_names_required_version(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    output = tmp_path / "output.json"
    output.write_text("{}", encoding="utf-8")
    result = robotcode_cli(["results", "show", "--output", str(output)], expect_ok=False)
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "Reading JSON result files requires Robot Framework 7.0+ (file: " in combined
    assert output.name in combined


# ---------------------------------------------------------------------------
# Result files with test metadata (Robot Framework 7.5+) on older versions
# ---------------------------------------------------------------------------


@pytest.mark.skipif(RF_VERSION >= (7, 5), reason="Robot Framework 7.5+ reads test metadata")
@pytest.mark.parametrize("subcommand", ["summary", "show", "log", "stats"])
def test_xml_with_test_metadata_explains_needed_robot_version(subcommand: str, robotcode_cli: CliRunner) -> None:
    """Robot's bare `Incompatible child element` error gets a hint naming
    Robot Framework 7.5 and test metadata as the cause."""
    result = robotcode_cli(["results", subcommand, "--output", str(_TEST_METADATA_XML)], expect_ok=False)
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "Incompatible child element 'meta' for 'test'" in combined
    assert _TEST_METADATA_HINT in combined


@pytest.mark.skipif(
    not ((7, 2) <= RF_VERSION < (7, 5)),
    reason="only Robot Framework 7.2-7.4 fail at the test's `metadata` when reading the JSON file",
)
def test_json_with_test_metadata_explains_needed_robot_version(robotcode_cli: CliRunner) -> None:
    result = robotcode_cli(["results", "show", "--output", str(_TEST_METADATA_JSON)], expect_ok=False)
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "does not have attribute 'metadata'" in combined
    assert _TEST_METADATA_HINT in combined


def test_other_parse_errors_get_no_test_metadata_hint(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    broken = tmp_path / "broken.xml"
    broken.write_text("<robot><suite>", encoding="utf-8")
    result = robotcode_cli(["results", "show", "--output", str(broken)], expect_ok=False)
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "failed to parse" in combined
    assert "test metadata" not in combined


@needs_rf_75
def test_metadata_entry_without_a_name_is_no_metadata(
    json_result: JsonRunner, text_result: CliRunner, tmp_path: Path
) -> None:
    """A `Metadata` setting with nothing after it is an entry with an empty
    name and value. Robot leaves it out of `output.xml` but writes it to
    `output.json`."""
    data = json.loads(_TEST_METADATA_JSON.read_text(encoding="utf-8"))
    data["suite"]["metadata"] = {"": ""}
    data["suite"]["tests"][1]["metadata"] = {"": ""}
    output = tmp_path / "output.json"
    output.write_text(json.dumps(data), encoding="utf-8")

    shown = json_result("show", output_path=output)
    assert [(t["name"], t.get("metadata")) for t in shown["tests"]] == [
        ("With Metadata", {"Issue": "4409"}),
        ("Without Metadata", None),
    ]

    log = json_result("log", "--suite-info", output_path=output)
    assert all("metadata" not in suite for suite in log["suites"])
    assert [t.get("metadata") for t in log["tests"]] == [{"Issue": "4409"}, None]

    text = text_result("log", "--suite-info", output_path=output).stdout
    assert text.count("_Metadata:_") == 1
    assert "- _:_" not in text


@needs_rf_75
@pytest.mark.parametrize("output_path", [_TEST_METADATA_XML, _TEST_METADATA_JSON], ids=["xml", "json"])
def test_static_files_with_test_metadata_parse(output_path: Path, json_result: JsonRunner) -> None:
    data = json_result("show", output_path=output_path)
    assert [(t["name"], t.get("metadata")) for t in data["tests"]] == [
        ("With Metadata", {"Issue": "4409"}),
        ("Without Metadata", None),
    ]
