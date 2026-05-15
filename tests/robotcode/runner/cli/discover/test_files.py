"""Acceptance tests for `robotcode discover files`."""

import json
from pathlib import Path
from typing import Any, List, cast

from .conftest import CliRunner


def _files_json(robotcode_cli: CliRunner, *args: str, suite_path: Path) -> List[str]:
    """Run `discover files` with `-f json` and return the parsed list."""
    result = robotcode_cli(
        [
            "--root",
            str(suite_path.parent),
            "--format",
            "json",
            "discover",
            "files",
            *args,
            str(suite_path),
        ]
    )
    return cast(List[str], cast(Any, json.loads(result.stdout)))


def test_files_lists_robot_files(robotcode_cli: CliRunner, files_tree: Path) -> None:
    files = _files_json(robotcode_cli, suite_path=files_tree)
    names = {Path(p).name for p in files}
    assert "sub1.robot" in names
    assert "deep.robot" in names


def test_files_lists_resource_files(robotcode_cli: CliRunner, files_tree: Path) -> None:
    files = _files_json(robotcode_cli, suite_path=files_tree)
    names = {Path(p).name for p in files}
    assert "sub2.resource" in names


def test_files_skips_other_extensions(robotcode_cli: CliRunner, files_tree: Path) -> None:
    files = _files_json(robotcode_cli, suite_path=files_tree)
    names = {Path(p).name for p in files}
    assert "ignored.txt" not in names
    # .gitignore itself is not a .robot/.resource file either.
    assert ".gitignore" not in names


def test_files_respects_gitignore(robotcode_cli: CliRunner, files_tree: Path) -> None:
    """`files_tree/.gitignore` lists `ignored_by_git.robot` — that file
    must be filtered out even though its extension matches."""
    files = _files_json(robotcode_cli, suite_path=files_tree)
    names = {Path(p).name for p in files}
    assert "ignored_by_git.robot" not in names


def test_files_full_paths_absolute(robotcode_cli: CliRunner, files_tree: Path) -> None:
    files = _files_json(robotcode_cli, "--full-paths", suite_path=files_tree)
    assert all(Path(p).is_absolute() for p in files)


def test_files_default_relative(robotcode_cli: CliRunner, files_tree: Path) -> None:
    files = _files_json(robotcode_cli, suite_path=files_tree)
    # Relative paths must not start at the filesystem root.
    assert all(not p.startswith("/") for p in files)


def test_files_text_format_lists_paths(robotcode_cli: CliRunner, files_tree: Path) -> None:
    result = robotcode_cli(["--root", str(files_tree.parent), "discover", "files", str(files_tree)])
    assert "sub1.robot" in result.stdout
    assert "Total:" in result.stdout
