"""`repl-server` reports an error of its configuration after its server has started, as a run reports it, so that a
client that connects to the server is not left waiting for it."""

from pathlib import Path
from typing import Any, List

import pytest
from click.testing import CliRunner

import robotcode.robot.config.utils as config_utils
from robotcode.cli import robotcode


def test_an_error_of_the_configuration_shows_after_the_server_has_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    # keep a developer's user-level robot.toml out of the test
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    (tmp_path / "robot.toml").write_text("[profiles.ci]\n", encoding="utf-8")
    events: List[str] = []

    def start_server(*args: Any, **kwargs: Any) -> None:
        events.append("server")

    monkeypatch.setattr("robotcode.repl_server.cli.run_as_debugpy_hidden_task", start_server)

    result = CliRunner().invoke(robotcode, ["--no-color", "-p", "typo", "repl-server"])

    assert events == ["server"]
    assert result.exit_code == 252, result.output
    assert result.stderr.count("Error: No profile matches 'typo'.") == 1, result.stderr
