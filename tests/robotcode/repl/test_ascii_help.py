"""The help of the dot-commands is ASCII, so `.help` works on a stream in any encoding."""

import os
import subprocess
import sys
from pathlib import Path

from robotcode.repl.console_interpreter import ConsoleInterpreter

# Variables of the developer's environment that would decide the prompt instead of the test.
_PROMPT_VARIABLES = ("ROBOT_OPTIONS", "ROBOTCODE_REPL_SHOW_PROMPT", "ROBOTCODE_FORCE_AI_AGENT", "ROBOTCODE_NO_AI_AGENT")


def test_help_of_every_dot_command_is_ascii(tmp_path: Path) -> None:
    names = sorted(ConsoleInterpreter._dot_command_index()[0])
    stdin = ".help\n" + "".join(f".help {name}\n" for name in names) + ".exit\n"
    env = {k: v for k, v in os.environ.items() if k not in _PROMPT_VARIABLES}

    result = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "repl", "-d", str(tmp_path / "results")],
        cwd=tmp_path,
        input=stdin.encode("ascii"),
        capture_output=True,
        env={**env, "PYTHONIOENCODING": "ascii"},
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("ascii", "replace")
    assert len(names) > 20
    for name in names:
        assert f".{name}".encode() in result.stdout
    assert result.stdout.isascii(), sorted({c for c in result.stdout.decode("utf-8", "replace") if ord(c) > 127})
