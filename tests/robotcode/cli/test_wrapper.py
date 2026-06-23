"""Tests for the `wrapper` re-exec feature of the `robotcode` CLI.

The actual re-exec uses ``os.execvp`` to replace the process, so these tests
spawn ``robotcode`` in a real subprocess (the in-process ``CliRunner`` would
have its own process replaced). The wrapper is a small cross-platform Python
script that records its invocation and then ``execv``s the wrapped command.

``os.execvp`` only has POSIX replace-semantics, so the subprocess tests are
skipped on Windows.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pytest

from robotcode.plugin.click_helper.wrappable import is_wrappable

requires_posix_exec = pytest.mark.skipif(
    sys.platform == "win32",
    reason="the wrapper feature re-executes via POSIX os.execvp; not supported on Windows",
)

# Records `SESSION_KIND` (to prove the profile env is applied *before* the
# wrapper runs) into "<wrapper>.called", one line per invocation, then execs
# the wrapped command (sys.argv[1:] = the python interpreter + robotcode args).
_WRAPPER_PY = (
    "import os, sys\n"
    "with open(__file__ + '.called', 'a', encoding='utf-8') as f:\n"
    "    f.write(os.environ.get('SESSION_KIND', '<unset>') + '\\n')\n"
    "os.execv(sys.argv[1], sys.argv[1:])\n"
)


def _write_wrapper(path: Path) -> Path:
    path.write_text(_WRAPPER_PY, encoding="utf-8")
    return path


def _calls(wrapper: Path) -> List[str]:
    marker = Path(str(wrapper) + ".called")
    return marker.read_text(encoding="utf-8").splitlines() if marker.exists() else []


def _run_robotcode(
    project: Path, args: List[str], *, env: Optional[Dict[str, str]] = None
) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, "-m", "robotcode.cli", *args],
        cwd=project,
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


# --- the @wrappable marker is on the right commands (pure, all platforms) ----


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


# --- the re-exec behaviour (subprocess, POSIX only) --------------------------


@requires_posix_exec
def test_wrappable_command_runs_through_the_profile_wrapper(project: Path) -> None:
    wrapper = project / "wrap.py"
    result = _run_robotcode(project, ["-p", "x11", "run", "suite.robot"])
    assert result.returncode == 0, result.stderr
    # Wrapped exactly once (guard prevents a second wrap) and the profile's
    # env reached the wrapper, i.e. it was applied *before* the re-exec.
    assert _calls(wrapper) == ["xephyr"]


@requires_posix_exec
def test_guard_env_suppresses_wrapping(project: Path) -> None:
    """When an outer layer (the VS Code launcher applying its DAP wrapper) has
    already set ROBOTCODE_WRAPPER_APPLIED, the inner process must not wrap."""
    wrapper = project / "wrap.py"
    result = _run_robotcode(
        project,
        ["-p", "x11", "run", "suite.robot"],
        env={**os.environ, "ROBOTCODE_WRAPPER_APPLIED": "1"},
    )
    assert result.returncode == 0, result.stderr
    assert _calls(wrapper) == []


@requires_posix_exec
def test_no_wrapper_flag_disables_wrapping(project: Path) -> None:
    wrapper = project / "wrap.py"
    result = _run_robotcode(project, ["-p", "x11", "--no-wrapper", "run", "suite.robot"])
    assert result.returncode == 0, result.stderr
    assert _calls(wrapper) == []


@requires_posix_exec
def test_cli_wrapper_overrides_the_profile_wrapper(project: Path) -> None:
    profile_wrapper = project / "wrap.py"
    cli_wrapper = _write_wrapper(project / "cliwrap.py")
    result = _run_robotcode(
        project,
        ["-p", "x11", "--wrapper", f"{sys.executable} {cli_wrapper}", "run", "suite.robot"],
    )
    assert result.returncode == 0, result.stderr
    assert _calls(cli_wrapper) == ["xephyr"]
    assert _calls(profile_wrapper) == []


@requires_posix_exec
def test_non_wrappable_command_is_not_wrapped(project: Path) -> None:
    wrapper = project / "wrap.py"
    # `discover` only parses files; it must never run through the wrapper.
    _run_robotcode(project, ["-p", "x11", "discover", "all", "suite.robot"])
    assert _calls(wrapper) == []
