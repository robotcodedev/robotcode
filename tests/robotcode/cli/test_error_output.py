"""Tests for how robotcode writes an error that stops a command.

Such an error is written as `[ ERROR ] <message>`, as robotcode writes the errors it reports and goes on after, with
`ERROR` in the colour of errors when colours are on. An invalid option keeps Click's usage line and hint to `--help`
above it; the exit codes stay.
"""

from pathlib import Path

import click
import click.testing
import pytest
from click.testing import CliRunner, Result
from robot.errors import DATA_ERROR

import robotcode.robot.config.utils as config_utils
from robotcode.cli import robotcode

PROFILE_ERROR = "No profile matches 'typo'."
RED_ERROR = click.style("ERROR", fg="red")


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project with one test in `tests` whose `robot.toml` defines no profile `typo`."""
    monkeypatch.chdir(tmp_path)
    # keep a developer's user-level robot.toml, selected profiles, options and colour settings out of the test
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    monkeypatch.delenv("ROBOTCODE_PROFILES", raising=False)
    monkeypatch.delenv("ROBOT_OPTIONS", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    (tmp_path / "robot.toml").write_text("[profiles.ci]\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    hi\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """The output of the runner is a terminal, outside an AI-agent session."""
    monkeypatch.setattr(click.testing._NamedTextIOWrapper, "isatty", lambda self: True)
    monkeypatch.setattr("robotcode.cli.is_running_in_ai_agent", lambda: False)


def run_robotcode(*args: str) -> Result:
    return CliRunner().invoke(robotcode, ["--no-pager", *args])


def test_a_profile_that_does_not_exist_is_written_once_as_an_error(project: Path) -> None:
    result = run_robotcode("-p", "typo", "run", "-d", "out", "tests")

    assert result.exit_code == DATA_ERROR, result.output
    assert result.stderr.count(f"[ ERROR ] {PROFILE_ERROR}\n") == 1, result.stderr
    assert "Error:" not in result.stderr
    assert "\x1b[" not in result.stderr


def test_the_reported_and_the_stopping_error_are_written_alike(project: Path) -> None:
    (project / "robot.toml").write_text('default-profiles = ["typo"]\n\n[profiles.ci]\n', encoding="utf-8")

    reported = run_robotcode("run", "-d", "out", "tests")
    stopping = run_robotcode("-p", "typo", "run", "-d", "out", "tests")

    assert reported.exit_code == 0, reported.output
    assert f"[ ERROR ] {PROFILE_ERROR}\n" in reported.stderr
    assert stopping.exit_code == DATA_ERROR, stopping.output
    assert f"[ ERROR ] {PROFILE_ERROR}\n" in stopping.stderr


def test_the_error_is_red_with_color(project: Path) -> None:
    result = run_robotcode("--color", "-p", "typo", "run", "-d", "out", "tests")

    assert f"[ {RED_ERROR} ] {PROFILE_ERROR}" in result.stderr, result.stderr


def test_the_error_is_red_on_a_terminal(project: Path, terminal: None) -> None:
    result = run_robotcode("-p", "typo", "run", "-d", "out", "tests")

    assert f"[ {RED_ERROR} ] {PROFILE_ERROR}" in result.stderr, result.stderr


def test_the_error_has_no_colour_with_no_color_on_a_terminal(project: Path, terminal: None) -> None:
    result = run_robotcode("--no-color", "-p", "typo", "run", "-d", "out", "tests")

    assert f"[ ERROR ] {PROFILE_ERROR}" in result.stderr
    assert "\x1b[" not in result.stderr


def test_the_error_has_no_colour_with_the_no_color_variable_on_a_terminal(
    project: Path, terminal: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")

    result = run_robotcode("-p", "typo", "run", "-d", "out", "tests")

    assert f"[ ERROR ] {PROFILE_ERROR}" in result.stderr
    assert "\x1b[" not in result.stderr


@pytest.mark.parametrize(
    ("args", "command"),
    [
        (["--nonsense", "profiles", "list"], "robotcode"),
        (["profiles", "list", "--nonsense"], "robotcode profiles list"),
    ],
)
def test_an_invalid_option_keeps_the_usage_and_the_hint(project: Path, args: list[str], command: str) -> None:
    result = CliRunner().invoke(robotcode, args)

    assert result.exit_code == 2, result.output
    assert result.stderr.startswith(f"Usage: {command} [OPTIONS]"), result.stderr
    assert result.stderr.endswith(f"\nTry '{command} --help' for help.\n\n[ ERROR ] No such option '--nonsense'.\n"), (
        result.stderr
    )


# Errors that come before the root command has set up its application: a command name that does not exist, an
# invalid option of robotcode itself
BEFORE_THE_COMMAND = [
    pytest.param(["nonsense"], id="unknown command"),
    pytest.param(["--nonsense", "profiles", "list"], id="invalid option"),
]


@pytest.mark.parametrize("args", BEFORE_THE_COMMAND)
def test_an_error_before_the_command_is_red_on_a_terminal(project: Path, terminal: None, args: list[str]) -> None:
    result = CliRunner().invoke(robotcode, args)

    assert f"[ {RED_ERROR} ] " in result.stderr, result.stderr


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--no-color", "nonsense"], id="unknown command"),
        pytest.param(["--no-color"], id="missing command"),
        pytest.param(["--no-color", "--nonsense", "profiles", "list"], id="invalid option"),
        pytest.param(
            ["-p", "typo", "--nonsense", "--no-color", "profiles", "list"], id="no-color after an invalid option"
        ),
    ],
)
def test_an_error_before_the_command_has_no_colour_with_no_color_on_a_terminal(
    project: Path, terminal: None, args: list[str]
) -> None:
    result = CliRunner().invoke(robotcode, args)

    assert result.exit_code == 2, result.output
    assert "[ ERROR ] " in result.stderr, result.stderr
    assert "\x1b[" not in result.stderr


@pytest.mark.parametrize("args", BEFORE_THE_COMMAND)
def test_an_error_before_the_command_has_no_colour_in_an_ai_agent_session(
    project: Path, terminal: None, monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    monkeypatch.setattr("robotcode.cli.is_running_in_ai_agent", lambda: True)

    result = CliRunner().invoke(robotcode, args)

    assert "[ ERROR ] " in result.stderr, result.stderr
    assert "\x1b[" not in result.stderr


def test_an_unexpected_error_is_not_written_as_an_error(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def boom() -> None:
        raise RuntimeError("boom")

    monkeypatch.setitem(robotcode.commands, "boom", boom)

    with pytest.raises(RuntimeError, match="boom"):
        CliRunner().invoke(robotcode, ["boom"], catch_exceptions=False)
