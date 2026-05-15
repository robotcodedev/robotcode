"""Acceptance tests for `robotcode results diff`.

The two fixture suites are run with `robot --name Diff` so their tests
share full names — diff matches across the pair via `full_name`.

Expected diff: baseline → current
* new_failures: Diff.Test Beta (PASS → FAIL)
* added:       Diff.Test Delta
* removed:     Diff.Test Gamma
* new_passes / status_changes: empty
"""

import json as _json
from pathlib import Path
from typing import Any, Dict

from ._helpers import strip_ansi
from .conftest import CliRunner


def _diff_via_cli(robotcode_cli: CliRunner, baseline: Path, current: Path, *extra: str) -> Dict[str, Any]:
    """Run `results diff <baseline> <current> [extra...]` and parse JSON.

    `diff` takes positional args rather than `--output`, so the shared
    `json_result` fixture doesn't fit cleanly. We invoke the CLI runner
    directly and parse the JSON ourselves.
    """
    result = robotcode_cli(
        ["--format", "json", "results", "diff", str(baseline), str(current), *extra],
    )
    return _json.loads(result.stdout)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Full diff
# ---------------------------------------------------------------------------


def test_diff_baseline_to_current_full(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    """The whole diff: B is a new failure, D is added, C is removed."""
    data = _diff_via_cli(robotcode_cli, diff_baseline_output, diff_current_output)

    nf = data["newFailures"]
    assert len(nf) == 1
    assert nf[0]["fullName"] == "Diff.Test Beta"
    assert nf[0]["baselineStatus"] == "PASS"
    assert nf[0]["currentStatus"] == "FAIL"
    assert "Beta broke in current" in nf[0].get("currentMessage", "")

    added = data["added"]
    assert {x["fullName"] for x in added} == {"Diff.Test Delta"}

    removed = data["removed"]
    assert {x["fullName"] for x in removed} == {"Diff.Test Gamma"}

    # No status changes besides the PASS→FAIL one (which is in newFailures)
    assert data.get("statusChanges", []) == []
    assert data.get("newPasses", []) == []


# ---------------------------------------------------------------------------
# --only filtering
# ---------------------------------------------------------------------------


def test_diff_only_new_failures_drops_other_sections(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    data = _diff_via_cli(
        robotcode_cli,
        diff_baseline_output,
        diff_current_output,
        "--only",
        "new-failures",
    )
    # Sections that were filtered out are omitted from JSON (None → removed by
    # the `remove_defaults` serialiser).
    assert "newFailures" in data
    assert "added" not in data
    assert "removed" not in data
    assert "statusChanges" not in data
    assert "newPasses" not in data


def test_diff_only_multiple_categories(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    data = _diff_via_cli(
        robotcode_cli,
        diff_baseline_output,
        diff_current_output,
        "--only",
        "added",
        "--only",
        "removed",
    )
    assert "added" in data
    assert "removed" in data
    assert "newFailures" not in data


# ---------------------------------------------------------------------------
# --message-chars truncation
# ---------------------------------------------------------------------------


def test_diff_message_chars_truncates(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    """`--message-chars 5` truncates the diff entries' messages."""
    data = _diff_via_cli(
        robotcode_cli,
        diff_baseline_output,
        diff_current_output,
        "--message-chars",
        "5",
    )
    msg = data["newFailures"][0].get("currentMessage", "")
    assert len(msg) <= 10  # margin for an ellipsis character


# ---------------------------------------------------------------------------
# Filters apply to both sides
# ---------------------------------------------------------------------------


def test_diff_filter_include_applies_to_both_sides(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    """`--include smoke` filters both baseline and current before diffing.

    Test Gamma is tagged `regression` only, so with `--include smoke` it
    drops out of the baseline → no longer appears in `removed`.
    """
    data = _diff_via_cli(
        robotcode_cli,
        diff_baseline_output,
        diff_current_output,
        "--include",
        "smoke",
    )
    # Beta still fails (in both sides → newFailures)
    assert {x["fullName"] for x in data["newFailures"]} == {"Diff.Test Beta"}
    # Gamma is no longer in `removed` because it was filtered out of baseline
    removed_names = {x["fullName"] for x in data.get("removed") or []}
    assert "Diff.Test Gamma" not in removed_names


def test_diff_search_applies_to_both_sides(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    """`--search Beta` keeps only the Beta test in the diff."""
    data = _diff_via_cli(
        robotcode_cli,
        diff_baseline_output,
        diff_current_output,
        "--search",
        "Beta",
    )
    nf_names = {x["fullName"] for x in data.get("newFailures") or []}
    assert nf_names == {"Diff.Test Beta"}
    # Delta / Gamma don't match Beta → not in added/removed
    added_names = {x["fullName"] for x in data.get("added") or []}
    removed_names = {x["fullName"] for x in data.get("removed") or []}
    assert "Diff.Test Delta" not in added_names
    assert "Diff.Test Gamma" not in removed_names


# ---------------------------------------------------------------------------
# TEXT output
# ---------------------------------------------------------------------------


def test_diff_text_smoke(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    result = robotcode_cli(
        ["results", "diff", str(diff_baseline_output), str(diff_current_output)],
    )
    plain = strip_ansi(result.stdout)
    assert "Test Beta" in plain
    assert "Test Delta" in plain
    assert "Test Gamma" in plain


# ---------------------------------------------------------------------------
# Identity diff: baseline against itself is empty
# ---------------------------------------------------------------------------


def test_diff_identity_yields_no_changes(robotcode_cli: CliRunner, diff_baseline_output: Path) -> None:
    """A baseline diffed against itself produces no changes."""
    data = _diff_via_cli(robotcode_cli, diff_baseline_output, diff_baseline_output)
    assert data.get("newFailures", []) == []
    assert data.get("newPasses", []) == []
    assert data.get("statusChanges", []) == []
    assert data.get("added", []) == []
    assert data.get("removed", []) == []


# ---------------------------------------------------------------------------
# --full-paths
# ---------------------------------------------------------------------------


def test_diff_full_paths_keeps_rel_source(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    """`--full-paths` doesn't strip `relSource` from the JSON — both
    fields are always present so consumers have a stable schema."""
    data = _diff_via_cli(robotcode_cli, diff_baseline_output, diff_current_output, "--full-paths")
    new_failure = data["newFailures"][0]
    src = new_failure.get("source")
    assert src is not None
    assert Path(src).is_absolute()
    assert new_failure.get("relSource") is not None


def test_diff_default_includes_rel_source(
    robotcode_cli: CliRunner,
    diff_baseline_output: Path,
    diff_current_output: Path,
) -> None:
    data = _diff_via_cli(robotcode_cli, diff_baseline_output, diff_current_output)
    new_failure = data["newFailures"][0]
    assert new_failure.get("relSource") is not None
