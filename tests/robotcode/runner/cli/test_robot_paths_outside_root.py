"""Positional paths of `robot` are relative to the working directory. The run changes into the
project root, so a path inside the root is rewritten relative to it, and a path outside the root
is passed on as an absolute path instead of failing."""

from pathlib import Path

import pytest
from click.testing import CliRunner
from robot.errors import INFO_PRINTED

from robotcode.cli import robotcode


def _dry_robot(root: Path, *paths: str) -> str:
    result = CliRunner().invoke(
        robotcode,
        ["--no-color", "--no-pager", "--dry", "--root", str(root), "robot", *paths],
        catch_exceptions=False,
    )
    # a dry run ends like `--help`: the options and arguments are printed instead of running robot
    assert result.exit_code == INFO_PRINTED, result.output
    assert "Would execute robot" in result.output
    return result.output


def test_a_path_outside_the_root_is_passed_as_an_absolute_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    monkeypatch.chdir(outside)

    output = _dry_robot(root, ".")

    # `Path.cwd()` is what the run resolves the path against, so it is also what the output must show
    assert str(Path.cwd()) in output.splitlines()


def test_a_path_inside_the_root_stays_relative_to_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "project"
    (root / "sub").mkdir(parents=True)
    monkeypatch.chdir(root / "sub")

    output = _dry_robot(root, ".")

    assert "sub" in output.splitlines()
