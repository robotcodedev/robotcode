import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("branch", "expected_flag", "expected_returncode"),
    [
        ("main", "--nostatusrc", 0),
        ("feature/example", "--statusrc", 1),
    ],
)
def test_ci_profile_conditional_no_status_rc_controls_robot_exit_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    branch: str,
    expected_flag: str,
    expected_returncode: int,
) -> None:
    (tmp_path / "robot.toml").write_text(
        """\
default-profiles = ["ci"]

[profiles.ci]
enabled = { if = "environ.get('CI') == 'true'" }
no-status-rc = { if = "environ.get('CI_COMMIT_REF_NAME') == 'main'" }
""",
        encoding="utf-8",
    )
    (tmp_path / "suite.robot").write_text(
        """\
*** Test Cases ***
Fails
    Fail    expected failure
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("CI_COMMIT_REF_NAME", branch)
    user_dir = tmp_path / "user"
    for name in ("HOME", "XDG_CONFIG_HOME", "APPDATA", "LOCALAPPDATA"):
        monkeypatch.setenv(name, str(user_dir))
    monkeypatch.setenv("ROBOTCODE_CACHE_DIR", str(tmp_path / "cache"))

    result = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "--verbose", "run", "suite.robot"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
        env=os.environ.copy(),
    )
    output = result.stdout + result.stderr
    unexpected_flag = "--statusrc" if expected_flag == "--nostatusrc" else "--nostatusrc"

    assert result.returncode == expected_returncode, output
    assert "Selected profiles: ci" in output
    assert 'Using profile "ci".' in output
    assert "1 test, 0 passed, 1 failed" in output
    assert expected_flag in output
    assert unexpected_flag not in output
