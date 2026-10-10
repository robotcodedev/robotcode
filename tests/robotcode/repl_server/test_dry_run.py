import subprocess
import sys
from pathlib import Path


def test_dry_run_starts_no_server(tmp_path: Path) -> None:
    """`--dry repl-server` starts no server; it prints what robot would run and
    exits instead of keeping the process alive."""
    result = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "--dry", "repl-server"],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 251, result.stderr  # robot's dry-run exit code
    assert "Dry run, not executing any commands" in result.stdout
