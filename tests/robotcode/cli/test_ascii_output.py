"""robotcode's own text is ASCII: the help of every command and the messages
of the commands that don't belong to a package of their own."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterator, List, Tuple

import click
import pytest
from click.testing import CliRunner

from robotcode.cli import robotcode


def _commands(cmd: click.Command, ctx: click.Context, path: Tuple[str, ...]) -> Iterator[Tuple[str, click.Context]]:
    yield " ".join(path), ctx
    if isinstance(cmd, click.Group):
        for name in cmd.list_commands(ctx):
            sub = cmd.get_command(ctx, name)
            if sub is not None:
                yield from _commands(sub, click.Context(sub, info_name=name, parent=ctx), (*path, name))


def test_help_of_every_command_is_ascii() -> None:
    root = click.Context(robotcode, info_name="robotcode")
    found: Dict[str, List[str]] = {}
    count = 0
    for name, ctx in _commands(robotcode, root, ("robotcode",)):
        count += 1
        chars = sorted({c for c in ctx.command.get_help(ctx) if ord(c) > 127})
        if chars:
            found[name] = chars

    assert count > 30, "the walk should reach the plugin commands too"
    assert found == {}


def test_message_without_a_project_is_ascii(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "config", "root"],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
    )

    assert b"Cannot detect root folder." in result.stderr
    assert result.stderr.isascii()


def test_cache_output_is_ascii(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ROBOTCODE_CACHE_DIR", raising=False)
    (tmp_path / "robot.toml").write_text("", encoding="utf-8")
    (tmp_path / "suite.robot").write_text("*** Test Cases ***\nT\n    Log    x\n", encoding="utf-8")
    # in a process of its own: `analyze code` ends with `os._exit`
    env = {k: v for k, v in os.environ.items() if k != "ROBOTCODE_CACHE_DIR"}
    subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "analyze", "code"],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=300,
    )
    assert any(tmp_path.glob(".robotcode_cache/**/*")), "analyze code should have filled the cache"
    runner = CliRunner()

    for args in (["analyze", "cache", "info"], ["analyze", "cache", "list"]):
        result = runner.invoke(robotcode, ["--no-color", "--no-pager", *args])

        assert result.exit_code == 0, result.output
        assert result.output.isascii(), result.output
