"""robotcode's own text in the output of `results` and `discover` is ASCII.

The result files hold only ASCII data, so every character outside ASCII in
the output would be one that robotcode wrote itself.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set

import pytest

from .conftest import CliRunner, _run

_SUITE = """\
*** Settings ***
Metadata    Platform    linux

*** Test Cases ***
Login Works
    [Tags]    smoke
    IF    '${RUN}' == '2'    Fail    boom
Pay
    IF    '${RUN}' == '1'    Fail    Timeout after 5000 ms waiting for the payment page to finish loading completely
Later
    Skip    not ready
Screenshot
    Log    <img alt="screenshot" src="data:image/png;base64,iVBORw0KGgo=">    HTML
Old Keyword
    Log    Keyword 'Old' is deprecated.    WARN
"""


def _non_ascii(text: str) -> Set[str]:
    return {c for c in text if ord(c) > 127}


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Path]:
    """Two runs of the same suite: `Pay` fails in the first, `Login Works` in the second."""
    root = tmp_path_factory.mktemp("ascii")
    (root / "shop.robot").write_text(_SUITE, encoding="utf-8")
    out: Dict[str, Path] = {"suite": root / "shop.robot"}
    for run in ("1", "2"):
        output = root / f"run{run}" / "output.xml"
        options = ["--output", str(output), "--report", "NONE", "--log", "NONE", "--name", "Shop", "-v", f"RUN:{run}"]
        _run(["-m", "robot", *options, str(root / "shop.robot")], timeout=120.0)
        assert output.is_file()
        out[f"run{run}"] = output
    return out


def _commands(runs: Dict[str, Path]) -> List[List[str]]:
    one, two = str(runs["run1"]), str(runs["run2"])
    views = [a for v in ("tests", "failures", "elapsed", "messages", "environment") for a in ("--show", v)]
    return [
        ["results", "summary", "--failed", "-o", one],
        ["results", "show", "-o", one],
        ["results", "show", "--sort", "status", "--message-chars", "20", "-o", one],
        ["results", "log", "--timing", "-o", one],
        ["results", "log", "--max-depth", "0", "-o", one],
        ["results", "stats", "--by", "status", "--by", "tag", "--by", "suite", "-o", one],
        ["results", "diff", one, two],
        ["results", "compare", one, two, one, "--by", "tag", "--by", "suite", *views],
        ["results", "compare", one, two, "--group-by-metadata", "Platform", *views],
        ["discover", "all", str(runs["suite"])],
        ["discover", "tests", str(runs["suite"])],
        ["discover", "tags", str(runs["suite"])],
    ]


def test_own_text_of_every_command_is_ascii(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    found = {}
    for args in _commands(runs):
        result = robotcode_cli(args, expect_ok=False)
        assert result.returncode == 0, f"{args}: {result.stderr}"
        chars = _non_ascii(result.stdout + result.stderr)
        if chars:
            found[" ".join(args[:2])] = sorted(chars)
    assert found == {}


def test_status_as_a_name(robotcode_cli: CliRunner, runs: Dict[str, Path]) -> None:
    summary = robotcode_cli(["results", "summary", "-o", str(runs["run1"])]).stdout
    show = robotcode_cli(["results", "show", "-t", "Login Works", "-o", str(runs["run1"])]).stdout

    assert "- _Status:_ **FAIL**" in summary
    assert any(line.startswith("- **PASS** Shop.Login Works") for line in show.splitlines())


def test_ascii_equivalents(robotcode_cli: CliRunner, runs: Dict[str, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(runs["run1"].parent)

    summary = robotcode_cli(["results", "summary", "-o", "output.xml"]).stdout
    diff = robotcode_cli(["results", "diff", str(runs["run1"]), str(runs["run2"])]).stdout
    failures = robotcode_cli(
        ["results", "compare", str(runs["run1"]), str(runs["run2"]), "--show", "failures", "--message-chars", "20"]
    ).stdout
    log = robotcode_cli(["results", "log", "--timing", "-t", "Login Works", "-o", "output.xml"]).stdout

    assert summary.startswith("# Summary: output.xml")
    assert "**PASS** -> **FAIL**" in diff
    assert "Timeout after 5000 m..." in failures
    assert re.search(r"_\(\d\d:\d\d:\d\d, \d+ ms\)_", log), log


def test_user_data_as_it_is(robotcode_cli: CliRunner, tmp_path: Path) -> None:
    suite = tmp_path / "data.robot"
    suite.write_text("*** Test Cases ***\nGrüße ✓\n    Log    ok\n", encoding="utf-8")
    output = tmp_path / "output.xml"
    _run(["-m", "robot", "--output", str(output), "--report", "NONE", "--log", "NONE", str(suite)], timeout=120.0)

    show = robotcode_cli(["results", "show", "-o", str(output)]).stdout

    assert "Grüße ✓" in show


def test_summary_on_a_cp1252_stream(runs: Dict[str, Path]) -> None:
    """The case of #683: Python writes to a pipe on Windows in the ANSI code page."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    args = ["--no-color", "--no-pager", "results", "summary", "--failed", "-o", str(runs["run1"])]
    result = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", *args],
        capture_output=True,
        env=env,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr.decode("cp1252", "replace")
    assert result.stdout.isascii()


def test_json_names_outside_ascii_on_a_cp1252_stream(tmp_path: Path) -> None:
    suite = tmp_path / "data.robot"
    suite.write_text("*** Test Cases ***\nGrüße ✓\n    Log    ok\n", encoding="utf-8")
    output = tmp_path / "output.xml"
    _run(["-m", "robot", "--output", str(output), "--report", "NONE", "--log", "NONE", str(suite)], timeout=120.0)
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}

    result = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "--format", "json", "results", "show", "-o", str(output)],
        capture_output=True,
        env=env,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr.decode("cp1252", "replace")
    assert result.stdout.isascii()
    assert [t["name"] for t in json.loads(result.stdout)["tests"]] == ["Grüße ✓"]


def test_colors_on_a_cp1252_stream(runs: Dict[str, Path]) -> None:
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    args = ["results", "summary", "--failed", "-o", str(runs["run1"])]

    colored = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "--color", "--no-pager", *args],
        capture_output=True,
        env=env,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )
    plain = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "--no-color", "--no-pager", *args],
        capture_output=True,
        env=env,
        stdin=subprocess.DEVNULL,
        timeout=120,
    )

    assert colored.returncode == 0, colored.stderr.decode("cp1252", "replace")
    assert colored.stdout == plain.stdout
