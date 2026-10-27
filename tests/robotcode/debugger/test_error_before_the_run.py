import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional, Tuple

import click
import pytest

from robotcode.core.types import ServerMode
from robotcode.core.utils.net import find_free_port
from robotcode.debugger.dap_types import Event
from robotcode.debugger.run import run_debugger
from robotcode.plugin import Application


class _Protocol:
    """A connected client that notes what stderr holds when the debugger reports the end of the run."""

    connected = True

    def __init__(self, capsys: pytest.CaptureFixture[str]) -> None:
        self.capsys = capsys
        self.stderr_at_robot_exited: Optional[str] = None

    def send_event(self, event: Event) -> None:
        if event.event == "robotExited":
            self.stderr_at_robot_exited = self.capsys.readouterr().err

    def terminate(self) -> None:
        pass

    def exit(self, exit_code: int) -> None:
        pass

    def wait_for_disconnected(self) -> bool:
        return True


def _run_with_an_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception = click.ClickException("No profile matches 'typo'."),
) -> Tuple[_Protocol, click.ClickException]:
    """Runs the debugger with a robot command that stops with `error`, by default one robotcode reports itself."""
    protocol = _Protocol(capsys)
    server = SimpleNamespace(protocol=protocol, loop=SimpleNamespace(stop=lambda: None))

    def run_robot(ctx: click.Context, app: Application, args: List[str]) -> int:
        raise error

    monkeypatch.setattr("robotcode.debugger.run.run_as_debugpy_hidden_task", lambda *args: None)
    monkeypatch.setattr("robotcode.debugger.run.wait_for_server", lambda: server)
    monkeypatch.setattr("robotcode.debugger.run._run_robot", run_robot)
    monkeypatch.setattr(
        "robotcode.debugger.run.Debugger",
        SimpleNamespace(
            instance=SimpleNamespace(
                start=lambda: None,
                set_main_thread=lambda thread: None,
                robot_report_file=None,
                robot_log_file=None,
                robot_output_file=None,
            )
        ),
    )

    with pytest.raises(click.ClickException) as raised:
        run_debugger(click.Context(click.Command("debug")), Application(), [], ServerMode.TCP, None, 0)
    return protocol, raised.value


def test_the_error_is_on_stderr_before_the_debugger_reports_the_end_of_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The debug launcher forwards the output of the run to VS Code's Debug Console only while the session lasts."""
    protocol, _ = _run_with_an_error(monkeypatch, capsys)

    assert protocol.stderr_at_robot_exited == "[ ERROR ] No profile matches 'typo'.\n"


def test_an_error_that_is_not_robotcodes_own_is_on_stderr_before_the_debugger_reports_the_end_of_the_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    protocol, error = _run_with_an_error(monkeypatch, capsys, ValueError("boom"))

    assert protocol.stderr_at_robot_exited == "[ ERROR ] boom\n"
    # the exit code of `debug` for such an error
    assert error.exit_code == 255


def test_the_raised_error_shows_nothing_and_keeps_its_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, error = _run_with_an_error(monkeypatch, capsys)
    capsys.readouterr()

    error.show()

    assert capsys.readouterr().err == ""
    assert error.exit_code == 1


def test_a_broken_configuration_ends_the_debug_command_with_252_and_one_error(tmp_path: Path) -> None:
    (tmp_path / "robot.toml").write_text("output-dir = 5\n", encoding="utf-8")
    (tmp_path / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robotcode.cli",
            "debug",
            "--no-wait-for-client",
            "--tcp",
            str(find_free_port()),
            "suite.robot",
        ],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 252, result.stderr
    assert result.stderr.count("[ ERROR ]") == 1, result.stderr
    assert "output_dir" in result.stderr


def test_a_profile_that_does_not_exist_ends_the_debug_command_with_252_after_the_server_started(
    tmp_path: Path,
) -> None:
    (tmp_path / "robot.toml").write_text("[profiles.ci]\n", encoding="utf-8")
    (tmp_path / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robotcode.cli",
            "-v",
            "-p",
            "typo",
            "debug",
            "--no-wait-for-client",
            "--tcp",
            str(find_free_port()),
            "suite.robot",
        ],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 252, result.stderr
    assert result.stderr.count("[ ERROR ] No profile matches 'typo'.") == 1, result.stderr
    # in the debug session, where the debug launcher passes it on to the client
    assert result.stderr.index("Start robotcode debugger thread") < result.stderr.index("[ ERROR ]"), result.stderr
