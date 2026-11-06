"""Exit codes of robotcode commands that pass on a Robot Framework exit code.

These commands answer with Robot Framework's exit codes, where 1-250 counts the
failed tests. An error robotcode reports itself for them exits with 252, Robot
Framework's code for invalid data or command line options. The tests drive
`robotcode` in a real subprocess, since the process exit code is the subject.

The `results` commands use their lower exit codes for what they found, so every
error that stops them exits with 128.
"""

import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

from robotcode.plugin.click_helper.exit_codes import has_robot_exit_codes
from robotcode.plugin.click_helper.wrappable import is_wrappable


def _run_robotcode(project: Path, args: List[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, "-m", "robotcode.cli", *args],
        cwd=project,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def broken_project(project: Path) -> Path:
    (project / "robot.toml").write_text("[robot\n", encoding="utf-8")
    return project


def test_robot_tool_commands_are_marked() -> None:
    from robotcode.runner.cli import discover, libdoc, rebot, testdoc

    for cmd in (rebot, libdoc, testdoc):
        assert has_robot_exit_codes(cmd), f"{cmd.name!r} should pass on Robot Framework's exit codes"
    assert not has_robot_exit_codes(discover)
    assert not is_wrappable(discover)


@pytest.mark.parametrize("extra", [[], ["--nostatusrc"]], ids=["default", "nostatusrc"])
def test_wrapper_that_cannot_be_started_exits_with_252(project: Path, extra: List[str]) -> None:
    result = _run_robotcode(project, ["--wrapper", "./does-not-exist", "robot", *extra, "-d", "out", "suite.robot"])

    assert result.returncode == 252, result.stderr
    assert "Failed to execute wrapper command" in result.stderr


def test_invalid_robot_toml_for_robot_exits_with_252(broken_project: Path) -> None:
    result = _run_robotcode(broken_project, ["robot", "-d", "out", "suite.robot"])

    assert result.returncode == 252, result.stderr
    assert "Invalid TOML file" in result.stderr


@pytest.mark.parametrize(
    "args",
    [["rebot", "-d", "out", "output.xml"], ["libdoc", "BuiltIn", "out.html"], ["testdoc", "suite.robot", "doc.html"]],
    ids=["rebot", "libdoc", "testdoc"],
)
def test_invalid_robot_toml_for_robot_tools_exits_with_252(broken_project: Path, args: List[str]) -> None:
    result = _run_robotcode(broken_project, args)

    assert result.returncode == 252, result.stderr
    assert "Invalid TOML file" in result.stderr


@pytest.fixture
def project_with_a_bad_expression(project: Path) -> Path:
    (project / "robot.toml").write_text('output-dir = { expr = "nope(" }\n', encoding="utf-8")
    return project


def test_expression_that_cant_be_evaluated_for_robot_exits_with_252(project_with_a_bad_expression: Path) -> None:
    result = _run_robotcode(project_with_a_bad_expression, ["robot", "suite.robot"])

    assert result.returncode == 252, result.stderr
    assert "[ ERROR ] Evaluation of 'output_dir' failed" in result.stderr
    assert "Traceback" not in result.stderr


def test_expression_that_cant_be_evaluated_for_discover_exits_with_1(project_with_a_bad_expression: Path) -> None:
    result = _run_robotcode(project_with_a_bad_expression, ["discover", "tests", "suite.robot"])

    assert result.returncode == 1, result.stderr
    assert "[ ERROR ] Evaluation of 'output_dir' failed" in result.stderr
    assert "Traceback" not in result.stderr


def test_expression_that_cant_be_evaluated_for_profiles_show_is_reported_and_shown(
    project_with_a_bad_expression: Path,
) -> None:
    result = _run_robotcode(project_with_a_bad_expression, ["profiles", "show"])

    assert result.returncode == 0, result.stderr
    assert "[ ERROR ] Evaluation of 'output_dir' failed" in result.stderr
    assert "Traceback" not in result.stderr
    assert 'expr = "nope("' in result.stdout


def test_invalid_robot_toml_for_debug_exits_with_252(broken_project: Path) -> None:
    # `--dry` runs the configuration check without starting a debug session.
    result = _run_robotcode(broken_project, ["--dry", "debug", "-d", "out", "suite.robot"])

    assert result.returncode == 252, result.stderr
    assert "Invalid TOML file" in result.stderr


def test_unknown_option_exits_with_252(project: Path) -> None:
    result = _run_robotcode(project, ["repl", "--no-such-option"])

    assert result.returncode == 252, result.stderr
    assert "No such option" in result.stderr


def test_failed_tests_are_passed_on(project: Path) -> None:
    (project / "fail.robot").write_text("*** Test Cases ***\nT\n    Fail    boom\n", encoding="utf-8")

    result = _run_robotcode(project, ["robot", "-d", "out", "fail.robot"])

    assert result.returncode == 1, result.stderr


def test_option_rejected_by_robot_framework_keeps_its_252(project: Path) -> None:
    result = _run_robotcode(project, ["robot", "--nosuchoption", "suite.robot"])

    assert result.returncode == 252, result.stderr
    assert "option --nosuchoption not recognized" in result.stdout + result.stderr


@pytest.mark.parametrize("args", [["analyze", "code"], ["discover", "tests"]], ids=["analyze", "discover"])
def test_other_commands_keep_their_exit_code(broken_project: Path, args: List[str]) -> None:
    result = _run_robotcode(broken_project, args)

    assert result.returncode == 1, result.stderr
    assert "Invalid TOML file" in result.stderr


@pytest.fixture
def result_file(project: Path) -> Path:
    _run_robotcode(project, ["robot", "-d", "out", "suite.robot"])
    output = project / "out" / "output.xml"
    assert output.is_file()
    return output


def test_missing_result_file_for_results_exits_with_128(project: Path) -> None:
    result = _run_robotcode(project, ["results", "summary", "-o", "missing.xml"])

    assert result.returncode == 128, result.stderr
    assert "Result file not found" in result.stderr


def test_invalid_option_value_for_results_exits_with_128(result_file: Path) -> None:
    result = _run_robotcode(result_file.parent, ["results", "diff", "output.xml", "output.xml", "--only", "nope"])

    assert result.returncode == 128, result.stderr
    assert "Invalid value for '--only'" in result.stderr


def test_file_that_is_no_result_file_exits_with_128(result_file: Path) -> None:
    (result_file.parent / "new.xml").write_text("hello\n", encoding="utf-8")

    result = _run_robotcode(result_file.parent, ["results", "diff", "output.xml", "new.xml"])

    assert result.returncode == 128, result.stderr
    assert "failed to parse" in result.stderr


def test_invalid_robot_toml_for_results_exits_with_128(broken_project: Path) -> None:
    result = _run_robotcode(broken_project, ["results", "summary"])

    assert result.returncode == 128, result.stderr
    assert "Invalid TOML file" in result.stderr


def test_unknown_command_of_results_exits_with_128(project: Path) -> None:
    result = _run_robotcode(project, ["results", "nope"])

    assert result.returncode == 128, result.stderr
    assert "No such command" in result.stderr


def test_missing_file_for_the_exit_code_of_a_diff_exits_with_128(result_file: Path) -> None:
    result = _run_robotcode(result_file.parent, ["results", "diff", "output.xml", "missing.xml", "--exit-code"])

    assert result.returncode == 128, result.stderr
    assert "missing.xml" in result.stderr


def test_invalid_option_of_robotcode_before_results_keeps_its_2(project: Path) -> None:
    result = _run_robotcode(project, ["--nonsense", "results", "summary"])

    assert result.returncode == 2, result.stderr
    assert "No such option" in result.stderr
