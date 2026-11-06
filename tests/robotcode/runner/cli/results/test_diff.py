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
from typing import Any, Dict, List, Protocol

import pytest

from ._helpers import strip_ansi
from .conftest import CliResult, CliRunner, _run_robot


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


# ---------------------------------------------------------------------------
# --exit-code and --exit-code-mask
# ---------------------------------------------------------------------------

_BODIES = {"PASS": "Log    ok", "FAIL": "Fail    boom", "SKIP": "Skip    later"}

# Each current run differs from the baseline in the categories its name says.
_BASELINE = {"A": "PASS", "B": "PASS", "C": "FAIL", "D": "SKIP", "E": "PASS"}
_CURRENT_RUNS = {
    "same": _BASELINE,
    "new_failure": {**_BASELINE, "B": "FAIL"},
    "new_pass": {**_BASELINE, "C": "PASS"},
    "status_change": {**_BASELINE, "D": "FAIL"},
    "added": {**_BASELINE, "F": "PASS"},
    "removed": {k: v for k, v in _BASELINE.items() if k != "E"},
    "failure_and_removed": {k: v for k, v in {**_BASELINE, "B": "FAIL"}.items() if k != "E"},
    "failure_and_added": {**_BASELINE, "B": "FAIL", "F": "PASS"},
    "pass_added_removed": {k: v for k, v in {**_BASELINE, "C": "PASS", "F": "PASS"}.items() if k != "E"},
}


class ExitCodeRun(Protocol):
    def __call__(self, current: str, extra: List[str], *, json_output: bool = False) -> CliResult: ...


def _write_suite(path: Path, tests: Dict[str, str]) -> Path:
    lines = ["*** Test Cases ***"]
    for name, status in tests.items():
        lines.append(f"Test {name}")
        if name == "A":
            lines.append("    [Tags]    smoke")
        lines.append(f"    {_BODIES[status]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def exit_code_outputs(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Path]:
    """The baseline and every current run, each run with `--name Pair` so the tests share names."""
    root = tmp_path_factory.mktemp("diff_exit_codes")
    outputs = {
        "baseline": _run_robot(_write_suite(root / "baseline.robot", _BASELINE), root, "baseline", suite_name="Pair")
    }
    for name, tests in _CURRENT_RUNS.items():
        outputs[name] = _run_robot(_write_suite(root / f"{name}.robot", tests), root, name, suite_name="Pair")
    return outputs


@pytest.fixture
def diff_exit(robotcode_cli: CliRunner, exit_code_outputs: Dict[str, Path]) -> ExitCodeRun:
    """Run `results diff <baseline> <current run> [extra...]` and return the result."""

    def run(current: str, extra: List[str], *, json_output: bool = False) -> CliResult:
        args = ["--format", "json"] if json_output else []
        args += ["results", "diff", str(exit_code_outputs["baseline"]), str(exit_code_outputs[current]), *extra]
        return robotcode_cli(args, expect_ok=False)

    return run


def test_diff_exits_with_0_without_the_option(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("new_failure", [])

    assert result.returncode == 0
    assert "Pair.Test B" in strip_ansi(result.stdout)


@pytest.mark.parametrize(
    ("current", "code"),
    [
        ("same", 0),
        ("new_failure", 1),
        ("new_pass", 2),
        ("status_change", 4),
        ("added", 8),
        ("removed", 16),
        ("failure_and_removed", 17),
    ],
)
def test_exit_code_of_the_categories(diff_exit: ExitCodeRun, current: str, code: int) -> None:
    result = diff_exit(current, ["--exit-code"])

    assert result.returncode == code, result.stderr


def test_exit_code_counts_only_the_categories_of_only(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("failure_and_added", ["--only", "new-failures", "--exit-code"], json_output=True)

    assert result.returncode == 1, result.stderr
    data = _json.loads(result.stdout)
    assert [c["fullName"] for c in data["newFailures"]] == ["Pair.Test B"]
    assert "added" not in data


def test_exit_code_of_a_category_without_entries_is_0(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("new_failure", ["--only", "added", "--exit-code"])

    assert result.returncode == 0, result.stderr


def test_exit_code_counts_only_the_tests_of_the_filters(diff_exit: ExitCodeRun) -> None:
    # the new failure is Test B, which has no tag `smoke`
    result = diff_exit("new_failure", ["--include", "smoke", "--exit-code"])

    assert result.returncode == 0, result.stderr


def test_masked_category_stays_in_the_output(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("failure_and_added", ["--exit-code", "--exit-code-mask", "added"], json_output=True)

    assert result.returncode == 1, result.stderr
    data = _json.loads(result.stdout)
    assert [c["fullName"] for c in data["newFailures"]] == ["Pair.Test B"]
    assert [c["fullName"] for c in data["added"]] == ["Pair.Test F"]


def test_several_masked_categories(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("pass_added_removed", ["--exit-code-mask", "new-passes,added", "--exit-code-mask", "removed"])

    assert result.returncode == 0, result.stderr


def test_mask_turns_on_the_exit_code(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("failure_and_added", ["--exit-code-mask", "added"])

    assert result.returncode == 1, result.stderr


def test_everything_masked(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("new_failure", ["--exit-code-mask", "all"], json_output=True)

    assert result.returncode == 0, result.stderr
    assert [c["fullName"] for c in _json.loads(result.stdout)["newFailures"]] == ["Pair.Test B"]


def test_unknown_mask_name_is_an_error(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("new_failure", ["--exit-code-mask", "nope"])

    assert result.returncode == 128
    assert "Invalid value for '--exit-code-mask': 'nope' is not one of" in result.stderr


def test_exit_code_with_json_output(diff_exit: ExitCodeRun) -> None:
    result = diff_exit("new_failure", ["--exit-code"], json_output=True)

    assert result.returncode == 1, result.stderr
    assert [c["fullName"] for c in _json.loads(result.stdout)["newFailures"]] == ["Pair.Test B"]


def test_help_names_the_exit_codes(robotcode_cli: CliRunner) -> None:
    text = strip_ansi(robotcode_cli(["results", "diff", "--help"]).stdout)

    for line in (
        "0    the diff is empty",
        "1    new failures",
        "2    new passes",
        "4    status changes",
        "8    added tests",
        "16   removed tests",
        "128  an error stopped the command",
    ):
        assert line in text
