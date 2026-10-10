import subprocess
import sys
from pathlib import Path


def test_dry_run_starts_no_debug_session(tmp_path: Path) -> None:
    """`--dry debug` starts no debug adapter and waits for no client; it prints
    what robot would run, including the debugger's listeners."""
    (tmp_path / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "--dry", "debug", "suite.robot"],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 251, result.stderr  # robot's dry-run exit code
    assert "Dry run, not executing any commands" in result.stdout
    assert "robotcode.debugger.listeners.ListenerV3" in result.stdout
