"""Tests for what the commands do when a profile name or pattern selects no profile.

Such a name stops a command before it runs anything, as a `robot.toml` with an invalid value does, whether it comes
from `-p` or `inherits`; a name from `default-profiles` is only reported. `profiles list` reports such names and lists
the profiles anyway. An `enabled` condition that cannot be evaluated stays a reported error, and profiles that inherit
each other stop a command.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner, Result
from robot.errors import DATA_ERROR, INFO_PRINTED

import robotcode.robot.config.utils as config_utils
from robotcode.cli import robotcode


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty project with one test in `tests`; each test writes its own `robot.toml`."""
    monkeypatch.chdir(tmp_path)
    # keep a developer's user-level robot.toml, selected profiles and options out of the test
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    monkeypatch.delenv("ROBOTCODE_PROFILES", raising=False)
    monkeypatch.delenv("ROBOT_OPTIONS", raising=False)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    hi\n", encoding="utf-8")
    return tmp_path


def run_robotcode(project: Path, robot_toml: str, *args: str) -> Result:
    (project / "robot.toml").write_text(robot_toml, encoding="utf-8")
    return CliRunner().invoke(robotcode, ["--no-color", "--no-pager", *args])


def test_a_mistyped_profile_stops_the_run_before_any_test(project: Path) -> None:
    result = run_robotcode(project, "[profiles.ci]\n", "-p", "missing", "run", "-d", "out", "tests")

    assert result.exit_code == DATA_ERROR, result.output
    assert result.output.count("No profile matches 'missing'.") == 1
    assert not (project / "out" / "output.xml").exists()


def test_a_pattern_without_a_match_stops_discover(project: Path) -> None:
    result = run_robotcode(project, "[profiles.ci]\n", "-p", "browser-*", "discover", "tests", "tests")

    assert result.exit_code != 0, result.output
    assert "No profile matches 'browser-*'." in result.output
    assert "Statistics" not in result.output


def test_a_default_profile_that_does_not_exist_is_reported_and_the_run_goes_on(project: Path) -> None:
    result = run_robotcode(project, 'default-profiles = ["typo"]\n\n[profiles.ci]\n', "run", "-d", "out", "tests")

    assert result.exit_code == 0, result.output
    assert result.output.count("No profile matches 'typo'.") == 1
    assert (project / "out" / "output.xml").exists()


def test_a_default_profile_of_the_user_configuration_that_the_project_replaces_is_reported(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_config = project / "user" / "robot.toml"
    user_config.parent.mkdir()
    user_config.write_text('default-profiles = ["mine"]\n\n[profiles.mine]\n', encoding="utf-8")
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: user_config)

    result = run_robotcode(project, "[profiles.ci]\n", "run", "-d", "out", "tests")

    assert result.exit_code == 0, result.output
    assert result.output.count("No profile matches 'mine'.") == 1
    assert (project / "out" / "output.xml").exists()


def test_an_inherited_profile_that_does_not_exist_stops_the_run(project: Path) -> None:
    result = run_robotcode(project, '[profiles.ci]\ninherits = ["typo"]\n', "-p", "ci", "run", "-d", "out", "tests")

    assert result.exit_code == DATA_ERROR, result.output
    assert "No profile matches 'typo'." in result.output
    assert not (project / "out" / "output.xml").exists()


def test_profiles_list_reports_a_name_that_selects_no_profile_and_lists_the_profiles(project: Path) -> None:
    robot_toml = '[profiles.ci]\ndescription = "CI server"\n'
    result = run_robotcode(project, robot_toml, "--format", "json", "-p", "missing", "-p", "ci", "profiles", "list")

    assert result.exit_code == 0, result.output
    assert "No profile matches 'missing'." in result.stderr
    listed = json.loads(result.stdout)
    assert [(p["name"], p["selected"]) for p in listed["profiles"]] == [("ci", True)]
    assert listed["unknownSelected"] == ["missing"]


def test_profiles_list_names_a_name_given_twice_once(project: Path) -> None:
    result = run_robotcode(
        project, "[profiles.ci]\n", "--format", "json", "-p", "typo", "-p", "typo", "profiles", "list"
    )

    assert result.exit_code == 0, result.output
    assert result.stderr.count("No profile matches 'typo'") == 1
    assert json.loads(result.stdout)["unknownSelected"] == ["typo"]


def test_profiles_that_inherit_each_other_stop_the_run(project: Path) -> None:
    robot_toml = '[profiles.a]\ninherits = ["b"]\n\n[profiles.b]\ninherits = ["a"]\n'

    result = run_robotcode(project, robot_toml, "-p", "a", "run", "-d", "out", "tests")

    assert result.exit_code == DATA_ERROR, result.output
    assert "The profile 'a' inherits itself: a -> b -> a." in result.output
    assert not (project / "out" / "output.xml").exists()


def test_profiles_list_names_no_unknown_names_for_a_valid_selection(project: Path) -> None:
    result = run_robotcode(project, "[profiles.ci]\n", "--format", "json", "-p", "ci", "profiles", "list")

    assert result.exit_code == 0, result.output
    assert "unknownSelected" not in json.loads(result.stdout)


def test_an_error_in_an_enabled_condition_is_reported_once_and_the_run_goes_on_without_the_profile(
    project: Path,
) -> None:
    robot_toml = """\
[profiles.ci]
enabled = { if = 'environ.get("CI") = "true"' }
extend-variables = { FROM_CI = "1" }
"""

    result = run_robotcode(project, robot_toml, "--dry", "-p", "ci", "run", "tests")

    # the dry run's own exit code: the command went on and showed what it would run
    assert result.exit_code == INFO_PRINTED, result.output
    assert result.output.count("Error evaluating 'enabled' condition for profile 'ci'") == 1
    assert "FROM_CI" not in result.output
