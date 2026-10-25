"""The start of the language server loads the configuration and passes its errors on to the server.

A name that selects no profile, a `robot.toml` that cannot be loaded or profiles that inherit each other do not keep
the server from starting.
"""

from pathlib import Path
from typing import Any, Dict

import pytest
from click.testing import CliRunner

import robotcode.robot.config.utils as config_utils
from robotcode.cli import robotcode


@pytest.fixture
def start_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Starts the language server in an empty project with the given `robot.toml`, without running it."""
    monkeypatch.chdir(tmp_path)
    # keep a developer's user-level robot.toml and selected profiles out of the test
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    monkeypatch.delenv("ROBOTCODE_PROFILES", raising=False)
    started: Dict[str, Any] = {}
    monkeypatch.setattr("robotcode.language_server.cli.run_server", lambda **kwargs: started.update(kwargs))

    def start(robot_toml: str, *profiles: str) -> Dict[str, Any]:
        (tmp_path / "robot.toml").write_text(robot_toml, encoding="utf-8")
        options = [o for p in profiles for o in ("-p", p)]
        result = CliRunner().invoke(robotcode, ["--no-color", *options, "language-server", "--stdio"])
        assert result.exit_code == 0, result.output
        started["log"] = result.stderr
        return started

    return start


# the editors report the names of their selection themselves, with a way to fix them
def test_a_name_of_the_selection_that_selects_no_profile_goes_only_to_the_log(start_server: Any) -> None:
    started = start_server('python-path = ["libraries"]\n\n[profiles.ci]\n', "missing")

    assert started["configuration_errors"] == []
    assert "No profile matches 'missing'." in started["log"]
    assert [str(p) for p in started["profile"].python_path] == ["libraries"]


# no editor reports a name of the environment, so the server shows it
def test_a_name_from_robotcode_profiles_that_selects_no_profile_is_passed_on(
    start_server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ROBOTCODE_PROFILES", "missing")

    started = start_server('python-path = ["libraries"]\n\n[profiles.ci]\n')

    assert started["configuration_errors"] == ["No profile matches 'missing'."]
    assert [str(p) for p in started["profile"].python_path] == ["libraries"]


def test_profiles_that_inherit_each_other_are_passed_on_and_the_server_starts_without_a_profile(
    start_server: Any,
) -> None:
    started = start_server('[profiles.a]\ninherits = ["b"]\n\n[profiles.b]\ninherits = ["a"]\n', "a")

    assert started["configuration_errors"] == ["The profile 'a' inherits itself: a -> b -> a."]
    assert started["profile"] is None


def test_a_default_profile_that_does_not_exist_is_passed_on_and_the_rest_of_the_configuration_applies(
    start_server: Any,
) -> None:
    started = start_server('default-profiles = ["typo"]\npython-path = ["libraries"]\n\n[profiles.ci]\n')

    assert started["configuration_errors"] == ["No profile matches 'typo'."]
    assert [str(p) for p in started["profile"].python_path] == ["libraries"]


def test_a_robot_toml_with_an_invalid_value_is_passed_on_and_the_server_starts_without_a_profile(
    start_server: Any,
) -> None:
    started = start_server("output-dir = 5\n")

    assert len(started["configuration_errors"]) == 1
    assert "robot.toml" in started["configuration_errors"][0]
    assert "output_dir" in started["configuration_errors"][0]
    assert started["profile"] is None


def test_a_configuration_without_errors_passes_on_none(start_server: Any) -> None:
    started = start_server('python-path = ["libraries"]\n\n[profiles.ci]\n', "ci")

    assert started["configuration_errors"] == []
