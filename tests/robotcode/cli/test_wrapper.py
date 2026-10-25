"""Tests for the `wrapper` re-run feature of the `robotcode` CLI.

The re-run spawns robotcode again under the wrapper and waits for it, so these
tests drive `robotcode` in a real subprocess (the in-process `CliRunner` would
recurse into itself). The wrapper is a small cross-platform Python script that
records its invocation and then runs the wrapped command. Everything is
spawn-and-wait, so the tests run on every platform.
"""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from click.testing import CliRunner

import robotcode.robot.config.utils as config_utils
from robotcode.cli import robotcode
from robotcode.core.utils.net import find_free_port
from robotcode.plugin.click_helper.wrappable import WRAPPER_APPLIED_ENV, is_wrappable

# Records `SESSION_KIND` (to prove the profile env is applied *before* the
# wrapper runs) into "<wrapper>.called", one line per invocation, then runs the
# wrapped command (sys.argv[1:] = the python interpreter + robotcode args).
_WRAPPER_PY = (
    "import os, subprocess, sys\n"
    "with open(__file__ + '.called', 'a', encoding='utf-8') as f:\n"
    "    f.write(os.environ.get('SESSION_KIND', '<unset>') + '\\n')\n"
    "sys.exit(subprocess.run(sys.argv[1:]).returncode)\n"
)


def _write_wrapper(path: Path) -> Path:
    path.write_text(_WRAPPER_PY, encoding="utf-8")
    return path


# A wrapper that records the command line it was handed (into "<path>.argv"),
# then runs it — used to inspect how the re-run reconstructed the invocation.
_RECORDER_PY = (
    "import subprocess, sys\n"
    "with open(__file__ + '.argv', 'w', encoding='utf-8') as f:\n"
    "    f.write(' '.join(sys.argv[1:]))\n"
    "sys.exit(subprocess.run(sys.argv[1:]).returncode)\n"
)


def _write_recorder(path: Path) -> Path:
    path.write_text(_RECORDER_PY, encoding="utf-8")
    return path


def _recorded_argv(recorder: Path) -> str:
    return Path(str(recorder) + ".argv").read_text(encoding="utf-8")


def _calls(wrapper: Path) -> List[str]:
    marker = Path(str(wrapper) + ".called")
    return marker.read_text(encoding="utf-8").splitlines() if marker.exists() else []


def _run_robotcode(
    project: Path, args: List[str], *, env: Optional[Dict[str, str]] = None
) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, "-m", "robotcode.cli", *args],
        cwd=project,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal robot.toml project with an `x11` profile that wraps the run."""
    wrapper = _write_wrapper(tmp_path / "wrap.py")
    (tmp_path / "robot.toml").write_text(
        "[profiles.x11]\n"
        f"wrapper = {json.dumps([sys.executable, str(wrapper)])}\n"
        "[profiles.x11.env]\n"
        'SESSION_KIND = "xephyr"\n',
        encoding="utf-8",
    )
    (tmp_path / "suite.robot").write_text(
        "*** Test Cases ***\nT\n    Should Be Equal    %{SESSION_KIND}    xephyr\n",
        encoding="utf-8",
    )
    return tmp_path


# --- the @wrappable marker is on the right commands (no subprocess) ----------


def test_execution_commands_are_marked_wrappable() -> None:
    from robotcode.debugger.cli import debug
    from robotcode.repl.cli import repl, robot_debug
    from robotcode.repl_server.cli import repl_server
    from robotcode.runner.cli import robot

    for cmd in (robot, debug, repl, robot_debug, repl_server):
        assert is_wrappable(cmd), f"{cmd.name!r} should be wrappable"


def test_non_execution_commands_are_not_wrappable() -> None:
    from robotcode.runner.cli import discover, libdoc, rebot, testdoc

    for cmd in (discover, libdoc, rebot, testdoc):
        assert not is_wrappable(cmd), f"{cmd.name!r} should not be wrappable"


# --- the re-run behaviour (spawns robotcode in a subprocess) -----------------


def test_wrappable_command_runs_through_the_profile_wrapper(project: Path) -> None:
    wrapper = project / "wrap.py"
    result = _run_robotcode(project, ["-p", "x11", "run", "suite.robot"])
    assert result.returncode == 0, result.stderr
    # Wrapped exactly once (guard prevents a second wrap) and the profile's
    # env reached the wrapper, i.e. it was applied *before* the re-exec.
    assert _calls(wrapper) == ["xephyr"]


def test_guard_env_suppresses_wrapping(project: Path) -> None:
    """The re-exec sets ROBOTCODE_WRAPPER_APPLIED before replacing the process,
    so a robotcode that already runs under a wrapper must not wrap again."""
    wrapper = project / "wrap.py"
    result = _run_robotcode(
        project,
        ["-p", "x11", "run", "suite.robot"],
        env={**os.environ, "ROBOTCODE_WRAPPER_APPLIED": "1"},
    )
    assert result.returncode == 0, result.stderr
    assert _calls(wrapper) == []


def test_no_wrapper_flag_disables_wrapping(project: Path) -> None:
    wrapper = project / "wrap.py"
    result = _run_robotcode(project, ["-p", "x11", "--no-wrapper", "run", "suite.robot"])
    assert result.returncode == 0, result.stderr
    assert _calls(wrapper) == []


def test_cli_wrapper_overrides_the_profile_wrapper(project: Path) -> None:
    profile_wrapper = project / "wrap.py"
    cli_wrapper = _write_wrapper(project / "cliwrap.py")
    # `--wrapper` is shlex-split, so shell-quote the parts (the interpreter path
    # can contain spaces, e.g. macOS "Application Support").
    wrapper_arg = f"{shlex.quote(sys.executable)} {shlex.quote(str(cli_wrapper))}"
    result = _run_robotcode(
        project,
        ["-p", "x11", "--wrapper", wrapper_arg, "run", "suite.robot"],
    )
    assert result.returncode == 0, result.stderr
    assert _calls(cli_wrapper) == ["xephyr"]
    assert _calls(profile_wrapper) == []


def test_non_wrappable_command_is_not_wrapped(project: Path) -> None:
    wrapper = project / "wrap.py"
    # `discover` only parses files; it must never run through the wrapper.
    _run_robotcode(project, ["-p", "x11", "discover", "all", "suite.robot"])
    assert _calls(wrapper) == []


def test_reexec_goes_through_the_launcher_script(project: Path, tmp_path: Path) -> None:
    """When robotcode was started through a bundled entry (`--launcher-script` /
    the bundled `__main__`), the re-exec must reuse that entry — not
    `python -m robotcode.cli`, which a bundled interpreter can't import."""
    bundled_main = tmp_path / "bundled_main.py"  # stand-in for the bundled entry
    bundled_main.write_text("from robotcode.cli import robotcode\n\nrobotcode()\n", encoding="utf-8")
    recorder = _write_recorder(project / "record.py")

    result = _run_robotcode(
        project,
        [
            "--launcher-script",
            str(bundled_main),
            "--wrapper",
            f"{shlex.quote(sys.executable)} {shlex.quote(str(recorder))}",
            "-p",
            "x11",
            "run",
            "suite.robot",
        ],
    )
    assert result.returncode == 0, result.stderr
    recorded = _recorded_argv(recorder)
    assert str(bundled_main) in recorded  # re-exec went through the launcher script
    assert "-m robotcode.cli" not in recorded


def test_direct_start_ignores_bundled_main_env(project: Path, tmp_path: Path) -> None:
    """A directly started robotcode (no `--launcher-script`) must NOT be diverted
    to the bundled copy just because ROBOTCODE_BUNDLED_ROBOTCODE_MAIN is set — the
    extension sets that in every VS Code terminal."""
    broken = tmp_path / "must_not_run.py"
    broken.write_text("import sys\nsys.exit('the bundled entry must not be used here')\n", encoding="utf-8")
    recorder = _write_recorder(project / "record.py")

    result = _run_robotcode(
        project,
        ["--wrapper", f"{shlex.quote(sys.executable)} {shlex.quote(str(recorder))}", "-p", "x11", "run", "suite.robot"],
        env={**os.environ, "ROBOTCODE_BUNDLED_ROBOTCODE_MAIN": str(broken)},
    )
    assert result.returncode == 0, result.stderr  # succeeded => the broken bundled entry was not used
    recorded = _recorded_argv(recorder)
    assert "-m robotcode.cli" in recorded  # used the direct module entry
    assert str(broken) not in recorded


def test_wrapper_propagates_the_run_exit_code(project: Path) -> None:
    """The wrapper must not swallow the run's exit code (contract rule #1)."""
    (project / "fail.robot").write_text("*** Test Cases ***\nFails\n    Should Be Equal    1    2\n", encoding="utf-8")
    result = _run_robotcode(project, ["-p", "x11", "run", "fail.robot"])
    assert result.returncode != 0  # the failure propagated through the wrapper
    assert _calls(project / "wrap.py") == ["xephyr"]  # and it did run through the wrapper


def test_dry_run_prints_the_wrapper_instead_of_running_it(project: Path) -> None:
    """`--dry` must not start the wrapper, whose setup/teardown would bring a
    real environment up and down; it only names the wrapper."""
    wrapper = project / "wrap.py"
    result = _run_robotcode(project, ["--dry", "-p", "x11", "run", "suite.robot"])
    assert result.returncode == 251, result.stderr  # the run's own dry-run exit code
    assert _calls(wrapper) == []
    assert f"Would run robotcode under: {sys.executable} {wrapper}" in result.stdout


def test_an_unknown_profile_stops_the_run_before_the_wrapper_of_a_valid_one_starts(project: Path) -> None:
    """A name that selects no profile stops the command before anything starts,
    also the wrapper of a valid profile, and the error shows once."""
    result = _run_robotcode(project, ["-p", "nope", "-p", "x11", "run", "suite.robot"])
    assert result.returncode == 252, result.stderr
    assert _calls(project / "wrap.py") == []
    output = result.stdout + result.stderr
    assert output.count("No profile matches 'nope'") == 1


def test_a_reported_profile_error_keeps_the_wrapper_of_a_valid_profile(project: Path) -> None:
    """An error that is only reported, such as an `enabled` condition that cannot
    be evaluated, shows once, and the wrapper of a valid profile still applies."""
    with (project / "robot.toml").open("a", encoding="utf-8") as f:
        f.write("[profiles.broken]\nenabled = { if = '1 +' }\n")
    result = _run_robotcode(project, ["-p", "broken", "-p", "x11", "run", "suite.robot"])
    assert result.returncode == 0, result.stderr
    assert _calls(project / "wrap.py") == ["xephyr"]
    output = result.stdout + result.stderr
    assert output.count("Error evaluating 'enabled' condition for profile 'broken'") == 1


# --- the wrapper comes from the configuration of the command -----------------


def _write_robot_toml(folder: Path, content: str) -> None:
    (folder / "tests").mkdir(parents=True)
    (folder / "tests" / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")
    (folder / "robot.toml").write_text(content, encoding="utf-8")


def test_tests_of_a_project_below_the_current_folder_run_under_its_wrapper(tmp_path: Path) -> None:
    """robotcode finds the configuration of a run from the paths of its tests, here
    from the root of a repository, and takes the wrapper from that configuration."""
    (tmp_path / ".git").mkdir()
    shop = tmp_path / "projects" / "shop"
    wrapper = _write_wrapper(tmp_path / "wrap.py")
    _write_robot_toml(
        shop,
        'default-profiles = ["gui"]\n'
        "[profiles.gui]\n"
        f"wrapper = {json.dumps([sys.executable, str(wrapper)])}\n"
        "[profiles.gui.env]\n"
        'SESSION_KIND = "shop"\n',
    )

    result = _run_robotcode(tmp_path, ["run", str(Path("projects", "shop", "tests"))])

    assert result.returncode == 0, result.stderr
    assert _calls(wrapper) == ["shop"]


def test_tests_of_another_project_run_without_the_wrapper_of_the_current_one(tmp_path: Path) -> None:
    wrapper = _write_wrapper(tmp_path / "wrap.py")
    _write_robot_toml(
        tmp_path / "a",
        f'default-profiles = ["x11"]\n[profiles.x11]\nwrapper = {json.dumps([sys.executable, str(wrapper)])}\n',
    )
    _write_robot_toml(tmp_path / "b", 'output-dir = "results"\n')

    result = _run_robotcode(tmp_path / "a", ["run", str(Path("..", "b", "tests"))])

    assert result.returncode == 0, result.stderr
    assert _calls(wrapper) == []


@pytest.mark.parametrize(
    ("args", "exit_code"),
    [
        (["run", "log.robot"], 0),
        (["-p", "x11", "run", "log.robot"], 0),
        (["debug", "--no-wait-for-client", "--tcp", "{port}", "log.robot"], 0),
        (["--dry", "repl-server", "log.robot"], 251),  # the exit code of a dry run
        (["repl"], 0),  # reads its input from the empty stdin
        (["robot-debug", "--no-debugger-attached", "log.robot"], 0),
    ],
    ids=["run", "run under a wrapper", "debug", "repl-server", "repl", "robot-debug"],
)
def test_verbose_output_names_each_loaded_configuration_file_once(
    project: Path, args: List[str], exit_code: int
) -> None:
    """The command loads its configuration once; under a wrapper, robotcode under
    it shows the loading, and robotcode before the wrapper does not."""
    (project / "log.robot").write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")
    port = str(find_free_port())

    result = _run_robotcode(project, ["-v", *(port if a == "{port}" else a for a in args)])

    assert result.returncode == exit_code, result.stderr
    output = result.stdout + result.stderr
    loaded = [line for line in output.splitlines() if line.startswith("Load configuration from")]
    assert loaded, output
    assert len(loaded) == len(set(loaded)), output
    assert output.count("Use root at:") == 1, output


def test_a_configuration_that_cannot_be_loaded_starts_no_wrapper(project: Path) -> None:
    (project / "robot.toml").write_text("output-dir = 5\n", encoding="utf-8")
    cli_wrapper = _write_wrapper(project / "cliwrap.py")

    result = _run_robotcode(
        project, ["--wrapper", f"{shlex.quote(sys.executable)} {shlex.quote(str(cli_wrapper))}", "run", "suite.robot"]
    )

    assert result.returncode == 252, result.stderr
    assert _calls(cli_wrapper) == []
    assert result.stderr.count("Error:") == 1, result.stderr
    assert "output_dir" in result.stderr


@pytest.mark.parametrize(
    ("args", "start"),
    [
        (["debug", "--no-wait-for-client", "suite.robot"], "robotcode.debugger.run.run_as_debugpy_hidden_task"),
        (["repl-server", "suite.robot"], "robotcode.repl_server.cli.run_as_debugpy_hidden_task"),
        (["repl"], "robotcode.repl.cli._pick_interpreter"),
        (["robot-debug", "suite.robot"], "robotcode.repl.cli._pick_interpreter"),
    ],
    ids=["debug", "repl-server", "repl", "robot-debug"],
)
def test_a_command_starts_under_the_wrapper_before_it_starts_anything(
    project: Path, monkeypatch: pytest.MonkeyPatch, args: List[str], start: str
) -> None:
    """Starting robotcode under the wrapper replaces this process, so a server or an
    interpreter that the command started before would not run under the wrapper."""
    monkeypatch.chdir(project)
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    # the command sets them in this process; with `setenv`, monkeypatch restores them afterwards
    monkeypatch.setenv(WRAPPER_APPLIED_ENV, "")
    monkeypatch.setenv("SESSION_KIND", "")
    events: List[str] = []

    def record(event: str) -> Any:
        def stop(*args: Any, **kwargs: Any) -> None:
            events.append(event)
            raise SystemExit(0)

        return stop

    monkeypatch.setattr("robotcode.plugin.click_helper.wrappable.os.execvp", record("wrapper"))
    monkeypatch.setattr("robotcode.plugin.click_helper.wrappable.subprocess.run", record("wrapper"))
    monkeypatch.setattr(start, record("start"))

    CliRunner().invoke(robotcode, ["-p", "x11", *args])

    assert events == ["wrapper"]


# --- the wrapper is ignored or disabled, with a warning ----------------------


def test_wrapper_ignored_and_warns_on_non_wrappable_command(project: Path) -> None:
    result = _run_robotcode(project, ["--wrapper", "xvfb-run", "discover", "all", "suite.robot"])
    assert _calls(project / "wrap.py") == []  # discover never runs through the wrapper
    assert "Ignoring --wrapper" in result.stderr


def test_no_wrapper_overrides_wrapper_with_a_warning(project: Path) -> None:
    result = _run_robotcode(project, ["-p", "x11", "--no-wrapper", "--wrapper", "xvfb-run", "run", "suite.robot"])
    assert result.returncode == 0, result.stderr
    assert _calls(project / "wrap.py") == []  # --no-wrapper wins, nothing is wrapped
    assert "Ignoring --wrapper" in result.stderr
