"""Cross-subcommand acceptance tests for `--search` and `--search-regex`.

Search is shared by `summary`, `show`, `log` and `stats`. These tests pin
the two flag's semantics: substring is case-insensitive, regex is
case-sensitive (Python regex semantics, use `(?i)` for opt-in
case-insensitivity), and the two are mutually exclusive.
"""

from pathlib import Path

import pytest

from .conftest import CliRunner, JsonRunner

# ---------------------------------------------------------------------------
# Substring (--search)
# ---------------------------------------------------------------------------


def test_search_substring_matches_test_name(json_result: JsonRunner, basic_output: Path) -> None:
    data = json_result("show", "--search", "Failing", output_path=basic_output)
    assert {t["name"] for t in data["tests"]} == {"Failing Test"}


def test_search_substring_case_insensitive(json_result: JsonRunner, basic_output: Path) -> None:
    """`failing` matches `Failing Test`."""
    data = json_result("show", "--search", "failing", output_path=basic_output)
    assert len(data["tests"]) == 1
    assert data["tests"][0]["name"] == "Failing Test"


def test_search_substring_matches_failure_message(json_result: JsonRunner, basic_output: Path) -> None:
    """Substring search also looks inside the failure message text."""
    data = json_result("show", "--search", "Boom", output_path=basic_output)
    assert {t["name"] for t in data["tests"]} == {"Failing Test"}


# ---------------------------------------------------------------------------
# Regex (--search-regex)
# ---------------------------------------------------------------------------


def test_search_regex_is_case_sensitive_by_default(json_result: JsonRunner, basic_output: Path) -> None:
    """A regex like `Failing` matches the capitalised name only."""
    data = json_result("show", "--search-regex", "Failing", output_path=basic_output)
    assert {t["name"] for t in data["tests"]} == {"Failing Test"}
    # Same regex in lowercase finds nothing
    lower = json_result("show", "--search-regex", "failing", output_path=basic_output)
    assert lower["tests"] == []


def test_search_regex_inline_case_insensitive(json_result: JsonRunner, basic_output: Path) -> None:
    """`(?i)` re-enables case-insensitivity on a per-pattern basis."""
    data = json_result("show", "--search-regex", "(?i)failing", output_path=basic_output)
    assert {t["name"] for t in data["tests"]} == {"Failing Test"}


def test_search_regex_anchors_and_alternation(json_result: JsonRunner, basic_output: Path) -> None:
    """Regex metacharacters (anchors, alternation) work normally."""
    # `Three$` anchors at the end of the name → matches the single test.
    data2 = json_result("show", "--search-regex", "Three$", output_path=basic_output)
    assert {t["name"] for t in data2["tests"]} == {"Passing Test Three"}

    # An anchored pattern that can't match any searched field yields nothing.
    data = json_result("show", "--search-regex", "^XYZ_definitely_no_field$", output_path=basic_output)
    assert data["tests"] == []


# ---------------------------------------------------------------------------
# Search targets inside the log body
# ---------------------------------------------------------------------------


def test_search_in_log_matches_keyword_argument(json_result: JsonRunner, loops_and_branches_output: Path) -> None:
    """The `log` subcommand searches inside keyword arguments."""
    data = json_result("log", "--search", "cherry", output_path=loops_and_branches_output)
    # `cherry` appears as the Set Variable argument in `If Else Test`, and as a
    # loop value in `For In Test`.
    names = {t["fullName"] for t in data["tests"]}
    assert "Loops And Branches.If Else Test" in names
    assert "Loops And Branches.For In Test" in names


def test_search_against_tags_is_normalisation_aware(json_result: JsonRunner, tagged_output: Path) -> None:
    """`--search` against tags normalises both sides (Robot tag rules).

    `tagged.robot` has three tests tagged `norm tag`, `norm_tag`, `NormTag` —
    all the same tag under Robot's normalization. Searching for `norm_tag`
    (with underscore) finds them all even though only one test is literally
    tagged that way.
    """
    data = json_result("show", "--search", "norm_tag", output_path=tagged_output)
    names = {t["name"] for t in data["tests"]}
    assert names == {"Tag Norm Variant A", "Tag Norm Variant B", "Tag Norm Variant C"}


# ---------------------------------------------------------------------------
# Suite-level Documentation / Metadata
# ---------------------------------------------------------------------------


def test_search_matches_suite_documentation(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """A hit on a suite's `Documentation` keeps every test underneath."""
    data = json_result("show", "--search", "SUITE_DOC_TOKEN_alpha", output_path=keyword_meta_output)
    assert {t["name"] for t in data["tests"]} == {"Tagged Caller", "Plain Test"}


def test_search_matches_suite_metadata_value(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """Suite `Metadata` values are searched alongside the docstring."""
    data = json_result("show", "--search", "payments-squad", output_path=keyword_meta_output)
    assert {t["name"] for t in data["tests"]} == {"Tagged Caller", "Plain Test"}


def test_search_matches_suite_metadata_name(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """Suite `Metadata` names match too (`OwnerTeam` here)."""
    data = json_result("show", "--search", "OwnerTeam", output_path=keyword_meta_output)
    assert {t["name"] for t in data["tests"]} == {"Tagged Caller", "Plain Test"}


# ---------------------------------------------------------------------------
# Result-tree keyword metadata (doc / tags / timeout)
# ---------------------------------------------------------------------------


def test_search_matches_keyword_documentation(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """A user keyword's `[Documentation]` is searchable in the result tree."""
    data = json_result("show", "--search", "KW_DOC_TOKEN_beta", output_path=keyword_meta_output)
    # Only the test that calls `Helper With Metadata` should match.
    assert {t["name"] for t in data["tests"]} == {"Tagged Caller"}


def test_search_matches_keyword_tag(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """A user keyword's `[Tags]` are searchable (Robot's tag normalisation:
    case + whitespace + underscore are folded, so `kw tag probe` matches
    `KWTagProbe`)."""
    data = json_result("show", "--search", "kw tag probe", output_path=keyword_meta_output)
    assert {t["name"] for t in data["tests"]} == {"Tagged Caller"}


def test_search_matches_keyword_timeout(json_result: JsonRunner, keyword_meta_output: Path) -> None:
    """A user keyword's `[Timeout]` value is searchable as plain text."""
    data = json_result("show", "--search", "7 days", output_path=keyword_meta_output)
    assert {t["name"] for t in data["tests"]} == {"Tagged Caller"}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcommand", ["summary", "show", "log", "stats"])
def test_search_invalid_regex_usage_error(subcommand: str, robotcode_cli: CliRunner, basic_output: Path) -> None:
    """An unparseable regex yields a non-zero exit and a clear message."""
    result = robotcode_cli(
        ["results", subcommand, "--search-regex", "[unclosed", "--output", str(basic_output)],
        expect_ok=False,
    )
    assert result.returncode != 0
    assert "search-regex" in result.stderr.lower() or "invalid" in result.stderr.lower()


@pytest.mark.parametrize("subcommand", ["summary", "show", "log", "stats"])
def test_search_and_search_regex_are_mutually_exclusive(
    subcommand: str, robotcode_cli: CliRunner, basic_output: Path
) -> None:
    """Passing both flags is a usage error."""
    result = robotcode_cli(
        [
            "results",
            subcommand,
            "--search",
            "x",
            "--search-regex",
            "y",
            "--output",
            str(basic_output),
        ],
        expect_ok=False,
    )
    assert result.returncode != 0
    assert "mutually exclusive" in result.stderr.lower()
