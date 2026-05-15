"""Cross-subcommand acceptance tests for shared filter options.

These tests parametrize the *same* filter expression across `summary`,
`show`, `log` and `stats` and verify that the four subcommands all narrow
their result set to the same number of tests. The goal is to catch
regressions where one subcommand silently stops honouring a filter that
the others still respect.
"""

from pathlib import Path
from typing import Any, Dict

import pytest

from .conftest import JsonRunner


def _effective_test_count(subcommand: str, data: Dict[str, Any]) -> int:
    """Return the number of tests that survived the filter pipeline."""
    if subcommand == "summary":
        return int(data["counts"]["total"])
    if subcommand in ("show", "log"):
        return len(data.get("tests", []))
    if subcommand == "stats":
        # Aggregate across the default `--by status` section.
        for section in data.get("sections", []):
            if section.get("dimension") == "status":
                return sum(int(g["counts"]["total"]) for g in section.get("groups", []))
        return 0
    raise AssertionError(f"unhandled subcommand {subcommand!r}")


SUBCOMMANDS = ("summary", "show", "log", "stats")


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filter_status_pass_uniform(subcommand: str, json_result: JsonRunner, basic_output: Path) -> None:
    """`--status pass` reduces all four subcommands to 3 passing tests."""
    data = json_result(subcommand, "--status", "pass", output_path=basic_output)
    assert _effective_test_count(subcommand, data) == 3


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filter_include_tag_uniform(subcommand: str, json_result: JsonRunner, tagged_output: Path) -> None:
    """`--include smoke` reduces every subcommand to the 3 smoke-tagged tests."""
    data = json_result(subcommand, "--include", "smoke", output_path=tagged_output)
    assert _effective_test_count(subcommand, data) == 3


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filter_exclude_tag_uniform(subcommand: str, json_result: JsonRunner, tagged_output: Path) -> None:
    """`--exclude regression` removes 3 regression-tagged tests, leaving 8."""
    data = json_result(subcommand, "--exclude", "regression", output_path=tagged_output)
    assert _effective_test_count(subcommand, data) == 8


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filter_suite_glob_uniform(subcommand: str, json_result: JsonRunner, nested_output: Path) -> None:
    """A glob on `--suite` selects only the matching sub-suite."""
    data = json_result(subcommand, "--suite", "Nested.Child.A", output_path=nested_output)
    assert _effective_test_count(subcommand, data) == 2


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filter_test_glob_uniform(subcommand: str, json_result: JsonRunner, basic_output: Path) -> None:
    """`--test 'Passing Test ?'` matches the three single-char-suffix tests."""
    data = json_result(subcommand, "--test", "Passing Test *", output_path=basic_output)
    assert _effective_test_count(subcommand, data) == 3


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filter_by_longname_uniform(subcommand: str, json_result: JsonRunner, nested_output: Path) -> None:
    """`-bl` picks exactly the requested test."""
    data = json_result(
        subcommand,
        "-bl",
        "Nested.Child.A.Test In A One",
        output_path=nested_output,
    )
    assert _effective_test_count(subcommand, data) == 1


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filter_exclude_by_longname_uniform(subcommand: str, json_result: JsonRunner, nested_output: Path) -> None:
    """`-ebl` removes one specific test from the run; 3 remain."""
    data = json_result(
        subcommand,
        "-ebl",
        "Nested.Child.A.Test In A One",
        output_path=nested_output,
    )
    assert _effective_test_count(subcommand, data) == 3


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filter_no_match_yields_empty_result(subcommand: str, json_result: JsonRunner, basic_output: Path) -> None:
    """A filter that excludes everything reduces the count to 0 everywhere."""
    data = json_result(subcommand, "--include", "no-such-tag", output_path=basic_output)
    assert _effective_test_count(subcommand, data) == 0


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filters_applied_field_present_when_filtering(
    subcommand: str, json_result: JsonRunner, tagged_output: Path
) -> None:
    """`filtersApplied` reflects every filter the user passed."""
    data = json_result(
        subcommand,
        "--include",
        "smoke",
        "--status",
        "pass",
        output_path=tagged_output,
    )
    applied = data.get("filtersApplied")
    assert isinstance(applied, dict)
    assert "include" in applied
    assert "status" in applied


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_filters_applied_echoes_canonical_tag_pattern(
    subcommand: str, json_result: JsonRunner, tagged_output: Path
) -> None:
    """`include` / `exclude` echo the canonical form of the tag pattern.

    Single tags are normalised (`Bug 1` -> `bug1`); patterns Robot parses as
    a logical expression are echoed verbatim because each operand would
    need to be normalised individually.
    """
    data = json_result(
        subcommand,
        "--include",
        "BUG 1",
        "--exclude",
        "smokeANDregression",
        output_path=tagged_output,
    )
    applied = data["filtersApplied"]
    assert applied["include"] == ["bug1"]
    assert applied["exclude"] == ["smokeANDregression"]


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_no_filters_no_filters_applied_field(subcommand: str, json_result: JsonRunner, basic_output: Path) -> None:
    """Without any filter, the `filtersApplied` key is omitted from JSON."""
    data = json_result(subcommand, output_path=basic_output)
    assert "filtersApplied" not in data
