"""Acceptance tests for `robotcode results compare`.

The result files are written by `robot` in a temporary directory, all with
`--name Shop`, so that the runs share the full names of their tests.
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

import pytest
from robot.version import get_full_version

from robotcode.robot.utils import RF_VERSION

from .conftest import CliResult, CliRunner, _run

_BODIES = {"PASS": "Log    ok", "FAIL": "Fail    boom", "SKIP": "Skip    later"}
_URL = "http://shop/order/"


def _robot(root: Path, name: str, tests: Dict[str, str], *extra: str, settings: str = "", suffix: str = ".xml") -> Path:
    """Run the suite `tests` and return its `output.xml`.

    A test's value is its status; `+smoke` tags it, `FAIL:<message>` fails it with that message,
    `PASS:<seconds>` sleeps that long, and `WARN:<message>` logs that warning. `settings` goes into a
    `*** Settings ***` section.
    """
    suite = root / f"{name}.robot"
    lines = ["*** Settings ***", settings, ""] if settings else []
    lines.append("*** Test Cases ***")
    for test, status in tests.items():
        lines.append(test)
        status, _, tag = status.partition("+")
        status, _, message = status.partition(":")
        if tag:
            lines.append(f"    [Tags]    {tag}")
        if not message:
            lines.append(f"    {_BODIES[status]}")
        elif status == "PASS":
            lines.append(f"    Sleep    {message}")
        elif status == "WARN":
            lines.append(f"    Log    {message}    WARN")
        else:
            lines.append(f"    Fail    {message}")
    suite.write_text("\n".join(lines) + "\n", encoding="utf-8")
    output = root / f"{name}{suffix}"
    options = ["--output", str(output), "--report", "NONE", "--log", "NONE", "--name", "Shop", *extra]
    _run(["-m", "robot", *options, str(suite)], timeout=120.0)
    assert output.is_file(), f"robot wrote no {output}"
    return output


def _rebot(root: Path, name: str, *outputs: Path) -> Path:
    output = root / f"{name}.xml"
    _run(
        ["-m", "robot.rebot", "--output", str(output), "--report", "NONE", "--log", "NONE"] + [str(o) for o in outputs],
        timeout=120.0,
    )
    assert output.is_file(), f"rebot wrote no {output}"
    return output


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Path]:
    """Three runs started one after another, a file that `rebot` merged from the first and the last, a run
    without `Pay` and one with eight failed tests."""
    root = tmp_path_factory.mktemp("compare")
    out = {
        "old": _robot(root, "old", {"Login": "PASS+smoke", "Pay": "PASS", "Search": "PASS+slow"}),
        "new": _robot(root, "new", {"Login": "PASS+smoke", "Pay": "FAIL", "Search": "SKIP"}),
        "later": _robot(root, "later", {"Login": "FAIL+smoke", "Pay": "PASS"}),
    }
    out["merged"] = _rebot(root, "merged", out["old"], out["later"])
    out["without"] = _robot(root, "without", {"Login": "PASS+smoke"})
    out["many"] = _robot(root, "many", {f"T{i}": "FAIL" for i in range(1, 9)})
    out["fast"] = _robot(root, "fast", {"Wait": "PASS:0.01", "Login": "PASS"})
    out["slow"] = _robot(root, "slow", {"Wait": "PASS:0.4", "Login": "PASS"})
    out["chrome"] = _robot(
        root, "chrome", {"Login": "PASS"}, "--metadata", "Browser:chrome", "--metadata", "Env:staging"
    )
    for platform in ("linux", "windows"):
        for status in ("PASS", "FAIL"):
            out[f"{platform}_{status.lower()}"] = _robot(
                root, f"{platform}_{status.lower()}", {"Pay": status}, "--metadata", f"Platform:{platform}"
            )
    out["warned"] = _robot(root, "warned", {"Login": "WARN:Keyword 'Old' is deprecated since 7.1", "Pay": "PASS"})
    out["no_library"] = _robot(
        root, "no_library", {"Login": "PASS", "Pay": "PASS"}, settings="Library    NoSuchLibrary"
    )
    out["server"] = _robot(
        root,
        "server",
        {
            "Login": "PASS+smoke",
            "Pay": f"FAIL:500 Server Error for url: {_URL}4711",
            "Search": f"FAIL:500 Server Error for url: {_URL}4712",
        },
    )
    return out


def _compare(cli: CliRunner, *args: Any, json_output: bool = False) -> CliResult:
    prefix = ["--format", "json"] if json_output else []
    return cli([*prefix, "results", "compare", *[str(a) for a in args]], expect_ok=False)


def _json(cli: CliRunner, *args: Any) -> Dict[str, Any]:
    result = _compare(cli, *args, json_output=True)
    assert result.returncode == 0, result.stderr
    data: Dict[str, Any] = json.loads(result.stdout)
    return data


def _row(text: str, first_cell: str, index: int = 0) -> List[str]:
    """The cells of the `index`-th table row whose first cell is `first_cell`."""
    found = 0
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == first_cell:
            if found == index:
                return cells
            found += 1
    raise AssertionError(f"no row {first_cell!r} in:\n{text}")


def _numbers_and_files(data: Dict[str, Any]) -> List[Any]:
    return [(r["number"], Path(r["file"]["source"]).stem) for r in data["runs"]]


# ---------------------------------------------------------------------------
# Runs from the arguments, names
# ---------------------------------------------------------------------------


def test_two_paths_are_numbered(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["new"])

    assert _numbers_and_files(data) == [(1, "old"), (2, "new")]
    assert all("name" not in r for r in data["runs"])


def test_named_runs(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, f"linux={runs['old']}", f"windows={runs['new']}")

    assert [r["name"] for r in data["runs"]] == ["linux", "windows"]

    text = _compare(robotcode_cli, f"linux={runs['old']}", f"windows={runs['new']}")
    assert "| linux " in text.stdout
    assert "| windows " in text.stdout


def test_names_are_escaped_in_the_column_heads(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    text = _compare(robotcode_cli, f"a*b={runs['old']}", f"c_d={runs['new']}", "--by", "tag").stdout

    assert _row(text, "Name") == ["Name", "a\\*b", "c_d"]


def test_an_existing_file_with_an_equals_sign_is_a_path(
    robotcode_cli: CliRunner, runs: Dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutil.copy(runs["old"], tmp_path / "a=b.xml")
    monkeypatch.chdir(tmp_path)

    data = _json(robotcode_cli, "a=b.xml", runs["new"])

    assert "name" not in data["runs"][0]
    assert Path(data["runs"][0]["file"]["source"]).name == "a=b.xml"


def test_one_run_is_an_error(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    result = _compare(robotcode_cli, runs["old"])

    assert result.returncode == 128, result.stderr
    assert "at least two runs" in result.stderr


def test_missing_result_file_is_an_error(
    robotcode_cli: CliRunner, runs: Dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = _compare(robotcode_cli, runs["old"], "linux=missing.xml")

    assert result.returncode == 128, result.stderr
    assert "missing.xml" in result.stderr


def test_repeated_name_is_an_error(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    result = _compare(robotcode_cli, f"linux={runs['old']}", f"linux={runs['new']}")

    assert result.returncode == 128, result.stderr
    assert "'linux' is given twice" in result.stderr


# ---------------------------------------------------------------------------
# Order of the runs, the last runs
# ---------------------------------------------------------------------------


def test_runs_are_in_argument_order(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["new"], runs["old"])

    assert _numbers_and_files(data) == [(1, "new"), (2, "old")]


def test_runs_ordered_by_start_time(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["later"], runs["new"], runs["old"], "--run-order", "start-time")

    assert _numbers_and_files(data) == [(1, "old"), (2, "new"), (3, "later")]


def test_file_merged_by_rebot_is_ordered_by_its_earliest_suite(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    # `merged` holds `old` and `later`; `old` started before `new`
    data = _json(robotcode_cli, runs["new"], runs["merged"], "--run-order", "start-time")

    assert _numbers_and_files(data) == [(1, "merged"), (2, "new")]
    assert "startTime" not in data["runs"][0]


def test_last_runs_keep_their_numbers(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["new"], runs["later"], runs["old"], runs["new"], "--last", "3")

    assert _numbers_and_files(data) == [(3, "later"), (4, "old"), (5, "new")]


# ---------------------------------------------------------------------------
# Overview, filters, matching, exit code
# ---------------------------------------------------------------------------


def test_overview_only(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    result = _compare(robotcode_cli, runs["old"], runs["new"], runs["later"])

    assert result.returncode == 0, result.stderr
    assert "## Runs" in result.stdout
    assert "## Tests" not in result.stdout
    rows = [line for line in result.stdout.splitlines() if line.startswith("|  #")]
    assert [row.split("|")[1].strip() for row in rows] == ["#1", "#2", "#3"]


def test_overview_comes_before_a_view(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    result = _compare(robotcode_cli, runs["old"], runs["new"], "--show", "tests")

    assert result.returncode == 0, result.stderr
    assert 0 < result.stdout.index("## Runs") < result.stdout.index("## Tests")


def test_json_of_the_runs(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["new"])

    first, second = data["runs"]
    assert first["status"] == "PASS"
    assert first["counts"] == {"total": 3, "passed": 3, "failed": 0, "skipped": 0, "notRun": 0}
    assert second["status"] == "FAIL"
    assert second["counts"]["failed"] == 1
    assert second["counts"]["skipped"] == 1
    assert first["startTime"] < second["startTime"]
    # ISO 8601 like the other times, also from the legacy timestamps before Robot Framework 7
    assert first["file"]["generationTime"][:11].count("-") == 2
    assert first["file"]["generationTime"][10] == "T"
    assert first["elapsedSeconds"] >= 0
    assert list(data) == ["runs"]


def test_filters_apply_to_every_run(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["later"], "--include", "smoke")

    assert [r["counts"]["total"] for r in data["runs"]] == [1, 1]
    assert [r["counts"]["failed"] for r in data["runs"]] == [0, 1]
    assert data["filtersApplied"] == {"include": ["smoke"]}


def test_tests_are_matched_by_their_full_name(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["new"], "--show", "tests")

    pay = [t for t in data["tests"]["tests"] if t["fullName"] == "Shop.Pay"]
    assert len(pay) == 1
    assert pay[0]["statuses"] == ["PASS", "FAIL"]


def test_exit_code_is_0_with_failed_tests(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    result = _compare(robotcode_cli, runs["new"], runs["later"])

    assert result.returncode == 0, result.stderr


def test_broken_file_exits_with_128(robotcode_cli: CliRunner, runs: Dict[str, Path], tmp_path: Path) -> None:
    broken = tmp_path / "broken.xml"
    broken.write_text("hello\n", encoding="utf-8")

    result = _compare(robotcode_cli, runs["old"], broken)

    assert result.returncode == 128, result.stderr
    assert "failed to parse" in result.stderr


def test_help_names_the_views(robotcode_cli: CliRunner) -> None:
    result = robotcode_cli(["results", "compare", "--help"])

    for view in ("tests", "failures", "elapsed", "messages", "environment"):
        assert view in result.stdout


# ---------------------------------------------------------------------------
# Counts per tag or suite
# ---------------------------------------------------------------------------


def _cells(section: Dict[str, Any], name: str) -> List[Any]:
    group = next(g for g in section["groups"] if g["name"] == name)
    return [None if c is None else (c["counts"]["failed"], c["counts"]["total"]) for c in group["runs"]]


def test_counts_per_tag(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["later"], "--by", "tag")

    (section,) = data["sections"]
    assert section["dimension"] == "tag"
    assert _cells(section, "smoke") == [(0, 1), (1, 1)]
    # `slow` exists only in the first run
    assert _cells(section, "slow") == [(0, 1), None]

    text = _compare(robotcode_cli, runs["old"], runs["later"], "--by", "tag").stdout
    assert "## By Tag" in text
    assert _row(text, "smoke") == ["smoke", "0/1", "1/1"]
    assert _row(text, "slow") == ["slow", "0/1", "-"]


def test_counts_per_tag_and_suite(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["later"], "--by", "tag", "--by", "suite", "--by", "tag")

    assert [s["dimension"] for s in data["sections"]] == ["tag", "suite"]
    assert _cells(data["sections"][1], "Shop") == [(0, 3), (1, 2)]

    text = _compare(robotcode_cli, runs["old"], runs["later"], "--by", "tag", "--by", "suite").stdout
    assert text.index("## Runs") < text.index("## By Tag") < text.index("## By Suite")


def test_counts_sorted_by_the_last_run(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    by_failed = _json(robotcode_cli, runs["old"], runs["later"], "--by", "tag")
    by_name = _json(robotcode_cli, runs["old"], runs["later"], "--by", "tag", "--sort", "name")

    assert [g["name"] for g in by_failed["sections"][0]["groups"]] == ["smoke", "slow"]
    assert [g["name"] for g in by_name["sections"][0]["groups"]] == ["slow", "smoke"]


def test_top_limits_the_counts(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["later"], "--by", "tag", "--top", "1")

    assert [g["name"] for g in data["sections"][0]["groups"]] == ["smoke"]
    assert data["sections"][0]["truncated"] == 1

    text = _compare(robotcode_cli, runs["old"], runs["later"], "--by", "tag", "--top", "1").stdout
    assert "1 more not shown" in text


# ---------------------------------------------------------------------------
# Views, status of each test
# ---------------------------------------------------------------------------


def test_views_in_the_order_given(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    views = ["--show", "elapsed", "--show", "tests", "--show", "elapsed"]
    result = _compare(robotcode_cli, runs["old"], runs["new"], *views)

    assert result.returncode == 0, result.stderr
    assert result.stdout.index("## Runs") < result.stdout.index("## Elapsed") < result.stdout.index("## Tests")
    assert result.stdout.count("## Elapsed") == 1


def test_unknown_view_exits_with_128(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    result = _compare(robotcode_cli, runs["old"], runs["new"], "--show", "nope")

    assert result.returncode == 128, result.stderr
    assert "Invalid value for '--show'" in result.stderr


def test_status_of_a_test_added_later(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    files = [runs["without"]] * 4 + [runs["old"], runs["old"], runs["new"], runs["old"], runs["old"], runs["old"]]

    result = _compare(robotcode_cli, *files, "--show", "tests")

    assert result.returncode == 0, result.stderr
    assert _row(result.stdout, "Shop.Pay")[1:3] == ["`----PPFPPP`", "1/6"]


def test_tests_that_never_failed_are_not_listed(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["new"], "--show", "tests")

    assert [t["fullName"] for t in data["tests"]["tests"]] == ["Shop.Pay"]


def test_flaky_and_failing_since(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    old, new = runs["old"], runs["new"]
    data = _json(robotcode_cli, old, new, old, new, old, "--show", "tests")

    (pay,) = data["tests"]["tests"]
    assert pay["statuses"] == ["PASS", "FAIL", "PASS", "FAIL", "PASS"]
    assert pay["perGroup"] == [{"group": None, "failed": 2, "runs": 5, "flaky": True}]

    data = _json(robotcode_cli, old, old, new, new, "--show", "tests")
    assert data["tests"]["tests"][0]["perGroup"] == [
        {"group": None, "failed": 2, "runs": 4, "flaky": False, "failingSince": 3}
    ]

    text = _compare(robotcode_cli, old, old, new, new, "--show", "tests").stdout
    assert _row(text, "Shop.Pay")[1:] == ["`PPFF`", "2/4", "", "#3"]


def test_tests_sorted_by_failed_count_and_cut_by_top(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["many"], runs["new"], runs["many"], "--show", "tests", "--top", "5")

    assert [t["fullName"] for t in data["tests"]["tests"]] == ["Shop.T1", "Shop.T2", "Shop.T3", "Shop.T4", "Shop.T5"]
    assert data["tests"]["truncated"] == 4  # T6, T7, T8 and Pay

    text = _compare(robotcode_cli, runs["many"], runs["new"], "--show", "tests", "--top", "5").stdout
    assert "4 more not shown" in text


def test_statuses_in_json(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["without"], runs["old"], runs["new"], "--show", "tests")

    (pay,) = data["tests"]["tests"]
    assert pay["statuses"] == [None, "PASS", "FAIL"]
    assert pay["relSource"].endswith("new.robot") or pay["source"].endswith("new.robot")


# ---------------------------------------------------------------------------
# The same failure over tests and runs
# ---------------------------------------------------------------------------


def test_failures_with_different_numbers_are_one_group(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["server"], "--show", "failures")

    (failure,) = data["failures"]["failures"]
    assert failure["message"] == f"500 Server Error for url: {_URL}4711"
    assert failure["tests"] == ["Shop.Pay", "Shop.Search"]
    assert failure["runs"] == [0, 2]

    text = _compare(robotcode_cli, runs["old"], runs["server"], "--show", "failures").stdout
    assert _row(text, f"500 Server Error for url: {_URL}4711")[1:] == ["2", "#2", "0", "2"]


def test_first_run_of_a_failure(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    old, server = runs["old"], runs["server"]
    data = _json(robotcode_cli, old, old, server, server, server, "--show", "failures")

    (failure,) = data["failures"]["failures"]
    assert failure["perGroup"] == [{"group": None, "firstRun": 3}]
    assert failure["runs"] == [0, 0, 2, 2, 2]


def test_failures_sorted_by_their_number_of_tests(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["new"], runs["server"], runs["many"], "--show", "failures")

    assert [(f["message"], len(f["tests"])) for f in data["failures"]["failures"]] == [
        ("boom", 9),
        (f"500 Server Error for url: {_URL}4711", 2),
    ]


def test_message_chars_cuts_the_failure_messages(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["server"], "--show", "failures", "--message-chars", "20")

    assert data["failures"]["failures"][0]["message"] == "500 Server Error for..."


# ---------------------------------------------------------------------------
# Growth of elapsed times
# ---------------------------------------------------------------------------


def test_slower_test_and_suite_in_the_last_run(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["fast"], runs["fast"], runs["slow"], "--show", "elapsed")

    tests = {g["fullName"]: g for g in data["elapsed"]["tests"]}
    assert tests["Shop.Wait"]["growthSeconds"] > 0.3
    assert tests["Shop.Wait"]["lastSeconds"] > tests["Shop.Wait"]["medianSeconds"]
    assert data["elapsed"]["tests"][0]["fullName"] == "Shop.Wait"
    assert [g["fullName"] for g in data["elapsed"]["suites"]] == ["Shop"]

    text = _compare(robotcode_cli, runs["fast"], runs["fast"], runs["slow"], "--show", "elapsed").stdout
    assert "### Suites" in text
    assert _row(text, "Shop.Wait")[4].startswith("+")


def test_faster_test_is_not_listed(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["slow"], runs["slow"], runs["fast"], "--show", "elapsed")

    assert "Shop.Wait" not in [g["fullName"] for g in data["elapsed"]["tests"]]
    assert data["elapsed"]["suites"] == []


def test_test_in_one_run_only_is_not_listed(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["slow"], "--show", "elapsed")

    assert "Shop.Wait" not in [g["fullName"] for g in data["elapsed"]["tests"]]


# ---------------------------------------------------------------------------
# Messages of the runs
# ---------------------------------------------------------------------------


def test_new_warning(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["old"], runs["warned"], "--show", "messages")

    assert data["messages"]["counts"] == [{"level": "WARN", "runs": [0, 0, 1]}]
    (warning,) = data["messages"]["messages"]
    assert warning["level"] == "WARN"
    assert warning["message"] == "Keyword 'Old' is deprecated since 7.1"
    assert warning["perGroup"] == [{"group": None, "firstRun": 3, "lastRun": 3, "new": True, "gone": False}]

    text = _compare(robotcode_cli, runs["old"], runs["old"], runs["warned"], "--show", "messages").stdout
    assert _row(text, "WARN")[1:] == ["0", "0", "1"]
    assert _row(text, "WARN", 1)[1:5] == ["Keyword 'Old' is deprecated since 7.1", "#3", "#3", "new"]


def test_gone_error(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    no_library = runs["no_library"]
    # the message starts with the suite's path, which is long in the temp directories of macOS and Windows
    data = _json(robotcode_cli, no_library, no_library, runs["old"], "--show", "messages", "--message-chars", "0")

    errors = [m for m in data["messages"]["messages"] if m["level"] == "ERROR"]
    assert len(errors) == 1
    assert "NoSuchLibrary" in errors[0]["message"]
    assert errors[0]["runs"] == [1, 1, 0]
    assert errors[0]["perGroup"] == [{"group": None, "firstRun": 1, "lastRun": 2, "new": False, "gone": True}]


def test_messages_are_taken_before_the_filters(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["warned"], "--show", "messages", "--include", "nothing")

    assert data["messages"]["counts"] == [{"level": "WARN", "runs": [0, 1]}]


# ---------------------------------------------------------------------------
# Environment of the runs
# ---------------------------------------------------------------------------


def _split_generator(program: str) -> Dict[str, str]:
    """The fields of the generator that `robot` or `rebot` of the installed Robot Framework writes."""
    text = get_full_version(program)
    tool, version, rest = text.split(" ", 2)
    python, _, platform = rest.strip("()").removeprefix("Python ").partition(" on ")
    return {"generator": text, "tool": tool, "version": version, "python": python, "platform": platform}


def test_versions_and_metadata(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["chrome"], runs["old"], "--show", "environment")

    first, second = data["environment"]
    assert first == {"run": 1, **_split_generator("Robot"), "metadata": {"Browser": "chrome", "Env": "staging"}}
    assert second == {"run": 2, **_split_generator("Robot")}

    text = _compare(robotcode_cli, runs["chrome"], runs["old"], "--show", "environment").stdout
    robot = _split_generator("Robot")
    assert _row(text, "Run") == ["Run", "Written by", "Python", "OS", "Browser", "Env"]
    # the second row of each run, after the overview
    written_by = f"Robot {robot['version']}"
    assert _row(text, "#1", 1) == ["#1", written_by, robot["python"], robot["platform"], "chrome", "staging"]
    assert _row(text, "#2", 1)[4:] == ["", ""]


def test_file_written_by_rebot(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["old"], runs["merged"], "--show", "environment")

    assert data["environment"][1] == {"run": 2, **_split_generator("Rebot")}


def test_metadata_values_are_cut(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["chrome"], runs["old"], "--show", "environment", "--message-chars", "4")

    assert data["environment"][0]["metadata"] == {"Browser": "chro...", "Env": "stag..."}


@pytest.mark.skipif(RF_VERSION < (7, 2), reason="robot writes output.json from Robot Framework 7.2 on")
def test_environment_of_a_json_result_file(robotcode_cli: CliRunner, runs: Dict[str, Path], tmp_path: Path) -> None:
    json_file = _robot(tmp_path, "json_run", {"Login": "PASS"}, suffix=".json")

    data = _json(robotcode_cli, json_file, runs["old"], "--show", "environment")

    assert data["environment"][0] == {"run": 1, **_split_generator("Robot")}
    assert data["runs"][0]["file"]["generationTime"]


@pytest.mark.skipif(
    not (7, 0) <= RF_VERSION < (7, 2), reason="only rebot of Robot Framework 7.0 and 7.1 writes such a JSON file"
)
def test_json_result_file_without_a_generator(robotcode_cli: CliRunner, runs: Dict[str, Path], tmp_path: Path) -> None:
    json_file = tmp_path / "rebot.json"
    _run(
        ["-m", "robot.rebot", "--output", str(json_file), "--report", "NONE", "--log", "NONE", str(runs["old"])],
        timeout=120.0,
    )

    data = _json(robotcode_cli, json_file, runs["old"], "--show", "environment")

    assert data["environment"][0] == {"run": 1}
    assert data["environment"][1] == {"run": 2, **_split_generator("Robot")}


# ---------------------------------------------------------------------------
# Groups of runs
# ---------------------------------------------------------------------------


def _sum_rows(text: str) -> List[List[str]]:
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "_total_" in cells:
            rows.append(cells)
    return rows


def test_runs_of_a_group_stand_together(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    l1, l2, w1, w2 = runs["linux_pass"], runs["linux_fail"], runs["windows_pass"], runs["windows_fail"]

    data = _json(robotcode_cli, l1, w1, l2, w2, "--group-by-metadata", "Platform")

    assert _numbers_and_files(data) == [(1, "linux_pass"), (2, "linux_fail"), (3, "windows_pass"), (4, "windows_fail")]
    assert [r["group"] for r in data["runs"]] == ["linux", "linux", "windows", "windows"]
    assert data["groupByMetadata"] == "Platform"
    assert [(g["name"], g["runs"], g["counts"]["failed"]) for g in data["groups"]] == [
        ("linux", [1, 2], 1),
        ("windows", [3, 4], 1),
    ]

    text = _compare(robotcode_cli, l1, w1, l2, w2, "--group-by-metadata", "Platform").stdout
    assert [row[1] for row in _sum_rows(text)] == ["**linux**", "**windows**"]
    assert _row(text, "#3")[1] == "windows"


def test_run_without_the_metadata_forms_its_own_group(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    data = _json(robotcode_cli, runs["linux_pass"], runs["old"], runs["linux_fail"], "--group-by-metadata", "Platform")

    assert [(g.get("name"), g["runs"]) for g in data["groups"]] == [("linux", [1, 2]), (None, [3])]
    assert _numbers_and_files(data)[2] == (3, "old")


def test_fails_only_on_one_platform(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    lp, wp, wf = runs["linux_pass"], runs["windows_pass"], runs["windows_fail"]
    files = [lp, wf, lp, wf, lp, wp, lp, wf, lp, wf]

    data = _json(robotcode_cli, *files, "--group-by-metadata", "Platform", "--show", "tests")

    (pay,) = data["tests"]["tests"]
    assert [(g["group"], g["failed"], g["runs"]) for g in pay["perGroup"]] == [("linux", 0, 5), ("windows", 4, 5)]
    assert pay["perGroup"][1]["flaky"] is True
    assert pay["perGroup"][1]["failingSince"] == 9

    text = _compare(robotcode_cli, *files, "--group-by-metadata", "Platform", "--show", "tests").stdout
    assert "_Groups: linux, windows_" in text
    assert _row(text, "Shop.Pay")[1:] == ["`PPPPP FFPFF`", "0/5, 4/5", "-, yes", "-, #9"]


def test_last_runs_per_group(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    lp, lf, wp = runs["linux_pass"], runs["linux_fail"], runs["windows_pass"]
    files = [lp, wp, lp, wp, lp, wp, lf, wp, lf, wp]

    data = _json(robotcode_cli, *files, "--group-by-metadata", "Platform", "--last", "2")

    expected = [(4, "linux"), (5, "linux"), (9, "windows"), (10, "windows")]
    assert [(r["number"], r["group"]) for r in data["runs"]] == expected


def test_order_dependent_values_per_group(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    lp, lf, wf = runs["linux_pass"], runs["linux_fail"], runs["windows_fail"]
    # Pay: linux PF (failing since #2), windows FF (failing since #3); both groups have the message from their start
    views = ["--show", "tests", "--show", "failures"]
    data = _json(robotcode_cli, lp, wf, lf, wf, "--group-by-metadata", "Platform", *views)

    (pay,) = data["tests"]["tests"]
    assert [g["failingSince"] for g in pay["perGroup"]] == [2, 3]
    (failure,) = data["failures"]["failures"]
    assert failure["perGroup"] == [{"group": "linux", "firstRun": 2}, {"group": "windows", "firstRun": 3}]


def test_growth_and_new_messages_per_group(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    linux = ["--metadata", "Platform:linux"]
    windows = ["--metadata", "Platform:windows"]
    linux_slow = _robot(tmp_path, "linux_slow", {"Pay": "PASS:0.4"}, *linux)
    linux_fast = _robot(tmp_path, "linux_fast", {"Pay": "PASS:0.01"}, *linux)
    windows_fast = _robot(tmp_path, "windows_fast", {"Pay": "PASS:0.01"}, *windows)
    windows_slow = _robot(
        tmp_path, "windows_slow", {"Pay": "PASS:0.4", "Note": "WARN:Keyword 'Old' is deprecated."}, *windows
    )
    files = [linux_slow, windows_fast, linux_fast, windows_slow]

    data = _json(robotcode_cli, *files, "--group-by-metadata", "Platform", "--show", "elapsed", "--show", "messages")

    # Pay got faster on linux and slower on windows, measured against the median of its own group
    (pay,) = [g for g in data["elapsed"]["tests"] if g["fullName"] == "Shop.Pay"]
    assert pay["group"] == "windows"
    assert pay["medianSeconds"] < 0.2 < pay["lastSeconds"]
    (warning,) = data["messages"]["messages"]
    assert warning["perGroup"] == [
        {"group": "linux", "new": False, "gone": False},
        {"group": "windows", "firstRun": 4, "lastRun": 4, "new": True, "gone": False},
    ]
