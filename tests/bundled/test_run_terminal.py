"""`bundled/tool/utils/run_terminal.py`, the process of RobotCode's run terminal, closes the terminal on a single key
after a run, marks the end of each run for VS Code's shell integration after the line about the terminal's reuse,
and on Windows lets a variable of a run replace an inherited one whose name differs only in case."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).parents[2] / "bundled" / "tool" / "utils" / "run_terminal.py"


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_terminal", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("x", id="character"),
        pytest.param("ü", id="non-ascii-character"),
        pytest.param("\r", id="enter"),
        pytest.param("\x03", id="ctrl-c"),
        pytest.param("\x1b", id="escape"),
        pytest.param("\x1b[A", id="arrow-key"),
        pytest.param("\x1bOP", id="f1"),
        pytest.param("\x1b[15~", id="f5"),
        pytest.param("\x1b[1;5C", id="ctrl-arrow-key"),
        pytest.param("\xe0H", id="windows-arrow-key"),
        pytest.param("\x00;", id="windows-f1"),
    ],
)
def test_single_key(script: ModuleType, text: str) -> None:
    assert script.is_single_key(text)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("robot --version\r", id="line"),
        pytest.param("x\r", id="character-and-enter"),
        pytest.param("x\n", id="character-and-newline"),
        pytest.param("xy", id="two-characters"),
        pytest.param("\x1b[A\x1b[A", id="two-arrow-keys"),
    ],
)
def test_more_than_one_key(script: ModuleType, text: str) -> None:
    assert not script.is_single_key(text)


def test_end_of_command_with_exit_code(script: ModuleType) -> None:
    assert script.command_finished(0) == "\x1b]633;D;0\x07"
    assert script.command_finished(253) == "\x1b]633;D;253\x07"


def test_end_of_command_without_exit_code(script: ModuleType) -> None:
    assert script.command_finished(None) == "\x1b]633;D\x07"


def test_end_of_run_follows_the_line_about_the_reuse(script: ModuleType) -> None:
    # on the empty line below it, where the next command's prompt begins, so that its sticky scroll shows only the
    # command line
    assert script.end_of_run(0, closed=False) == (
        "\r\n\x1b[0m\x1b[7m * \x1b[0m Terminal will be reused by RobotCode runs, press any key to close it.\r\n"
        "\x1b]633;D;0\x07"
    )


def test_end_of_run_follows_the_line_about_closing(script: ModuleType) -> None:
    assert script.end_of_run(None, closed=True) == (
        "\r\n\x1b[0m\x1b[7m * \x1b[0m Press any key to close the terminal.\r\n\x1b]633;D\x07"
    )


def test_announces_rich_command_detection(script: ModuleType) -> None:
    # which VS Code's sticky scroll needs
    assert script.RICH_COMMAND_DETECTION == "\x1b]633;P;HasRichCommandDetection=True\x07"


def test_run_variable_replaces_another_spelling_on_windows(script: ModuleType) -> None:
    assert script.merged_environment({"Path": r"C:\Windows"}, {"path": r"C:\tools"}, windows=True) == {
        "path": r"C:\tools"
    }
    assert script.merged_environment({"PATH": r"C:\Windows"}, {"Path": r"C:\tools"}, windows=True) == {
        "Path": r"C:\tools"
    }


def test_run_variables_keep_other_variables_on_windows(script: ModuleType) -> None:
    base = {"PATH": r"C:\Windows", "TEMP": r"C:\Temp"}

    assert script.merged_environment(base, {"Path": r"C:\tools", "ROBOT_OPTIONS": "-L DEBUG"}, windows=True) == {
        "TEMP": r"C:\Temp",
        "Path": r"C:\tools",
        "ROBOT_OPTIONS": "-L DEBUG",
    }


def test_run_variable_keeps_another_spelling_on_other_platforms(script: ModuleType) -> None:
    assert script.merged_environment({"PATH": "/usr/bin"}, {"path": "/opt/bin"}, windows=False) == {
        "PATH": "/usr/bin",
        "path": "/opt/bin",
    }


def test_last_of_two_spellings_of_the_run_stays_on_windows(script: ModuleType) -> None:
    env = {"path": r"C:\from-robot-env", "Path": r"C:\from-launch-config"}

    assert script.merged_environment({"PATH": r"C:\Windows"}, env, windows=True) == {"Path": r"C:\from-launch-config"}
