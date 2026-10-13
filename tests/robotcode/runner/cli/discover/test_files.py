"""Acceptance tests for `robotcode discover files`."""

import json
import sys
from pathlib import Path
from typing import Any, List, cast

import pytest

from .conftest import CliRunner

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


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
    """Without `--full-paths`, paths are reported relative to the
    `--root` folder (the project root passed in via the fixture)."""
    files = _files_json(robotcode_cli, suite_path=files_tree)
    assert all(not p.startswith("/") for p in files)


def test_files_text_format_lists_paths(robotcode_cli: CliRunner, files_tree: Path) -> None:
    """TEXT output: H1 heading + bullet list of paths + italic `_Total:_` footer."""
    result = robotcode_cli(["--root", str(files_tree.parent), "discover", "files", str(files_tree)])
    assert "# Files" in result.stdout
    assert "sub1.robot" in result.stdout
    # Italic-label convention for the count footer.
    assert "_Total:_" in result.stdout


@pytest.mark.parametrize(
    ("cwd", "path", "expected"),
    [
        ("files_tree", "nested", ["files_tree/nested/deep.robot"]),
        (
            "files_tree/nested",
            "..",
            ["files_tree/nested/deep.robot", "files_tree/sub1.robot", "files_tree/sub2.resource"],
        ),
        ("files_tree/nested", "{root}/files_tree/nested", ["files_tree/nested/deep.robot"]),
    ],
)
def test_files_resolves_paths_against_the_working_directory(
    robotcode_cli: CliRunner,
    files_tree: Path,
    monkeypatch: pytest.MonkeyPatch,
    cwd: str,
    path: str,
    expected: List[str],
) -> None:
    """A path given in a subfolder of the root counts from that subfolder, like with `discover tests`."""
    root = files_tree.parent
    monkeypatch.chdir(root / cwd)
    result = robotcode_cli(["--root", str(root), "--format", "json", "discover", "files", path.format(root=root)])
    assert sorted(json.loads(result.stdout)) == expected


def test_files_takes_default_paths_from_the_root(
    robotcode_cli: CliRunner, files_tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default paths are configuration: they count from the root, also when started in a subfolder."""
    monkeypatch.chdir(files_tree)
    result = robotcode_cli(
        ["--root", str(files_tree.parent), "-dp", "files_tree/nested", "--format", "json", "discover", "files"]
    )
    assert json.loads(result.stdout) == ["files_tree/nested/deep.robot"]


def test_files_toml_format_lists_paths_under_data(robotcode_cli: CliRunner, files_tree: Path) -> None:
    """TOML needs a table at the top, so the list of paths is under `data`."""
    result = robotcode_cli(["--root", str(files_tree.parent), "--format", "toml", "discover", "files", str(files_tree)])
    names = {Path(p).name for p in tomllib.loads(result.stdout)["data"]}
    assert "sub1.robot" in names
    assert "deep.robot" in names


def test_files_keeps_the_order_of_the_given_paths(robotcode_cli: CliRunner, flat_suite: Path) -> None:
    """Several paths are walked in the order given, without duplicates, the same on every run."""
    suites = flat_suite.parent
    order = ["tagged.robot", "flat.robot", "tasks.robot", "tagged.robot", "metadata.robot"]
    files = _files_json(robotcode_cli, *(str(suites / name) for name in order[:-1]), suite_path=suites / order[-1])
    assert [Path(p).name for p in files] == ["tagged.robot", "flat.robot", "tasks.robot", "metadata.robot"]
