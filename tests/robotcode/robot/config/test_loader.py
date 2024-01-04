import os
from pathlib import Path
from typing import Iterator, Tuple

import pytest

from robotcode.robot.config.loader import (
    DiscoverdBy,
    find_project_root,
    get_config_files_from_folder,
)


@pytest.fixture
def temp_project(tmp_path: Path) -> Iterator[Path]:
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield Path(tmp_path)
    finally:
        os.chdir(old_cwd)


@pytest.mark.parametrize(
    ("path_str", "discovered_by"),
    {
        ("pyproject.toml", DiscoverdBy.PYPROJECT_TOML),
        ("robot.toml", DiscoverdBy.ROBOT_TOML),
    },
)
def test_find_project_root_from_root_from_toml_works(
    temp_project: Path, path_str: str, discovered_by: DiscoverdBy
) -> None:
    root_pyproject_toml = temp_project / path_str
    root_pyproject_toml.touch()

    root, discovery_by = find_project_root()
    assert root == temp_project
    assert discovery_by == discovered_by


@pytest.mark.parametrize(
    ("path_str", "discovered_by"),
    {(".git", DiscoverdBy.GIT), (".hg", DiscoverdBy.HG)},
)
def test_find_project_root_from_root_from_vcs_dirs_works(
    temp_project: Path, path_str: str, discovered_by: DiscoverdBy
) -> None:
    root_pyproject_toml = temp_project / path_str
    root_pyproject_toml.mkdir()

    root, discovery_by = find_project_root()
    assert root == temp_project
    assert discovery_by == discovered_by


def test_find_project_from_sub_dir_robot_toml_works(temp_project: Path) -> None:
    root_robot_toml = temp_project / "robot.toml"
    root_robot_toml.touch()

    sub_dir = temp_project / "subdir"
    sub_dir.mkdir()

    root, discovery_by = find_project_root(sub_dir)
    assert root == temp_project
    assert discovery_by == DiscoverdBy.ROBOT_TOML


def test_find_project_from_sub_dir_file_robot_toml_works(
    temp_project: Path,
) -> None:
    root_robot_toml = temp_project / "robot.toml"
    root_robot_toml.touch()

    sub_dir = temp_project / "subdir"
    sub_dir.mkdir()
    file = sub_dir / "file.robot"
    file.touch()

    root, discovery_by = find_project_root(file)
    assert root == temp_project
    assert discovery_by == DiscoverdBy.ROBOT_TOML


def test_find_project_from_sub_dir_file_robot_toml_no_root_found(
    temp_project: Path,
) -> None:
    sub_dir = temp_project / "subdir"
    sub_dir.mkdir()
    file = sub_dir / "file.robot"
    file.touch()

    root, discovery_by = find_project_root(file)
    assert root is None
    assert discovery_by == DiscoverdBy.NOT_FOUND


def test_find_project_from_several_sub_dirs_and_files_robot_toml_works(
    temp_project: Path,
) -> None:
    root_robot_toml = temp_project / "robot.toml"
    root_robot_toml.touch()

    sub_dir = temp_project / "subdir"
    sub_dir.mkdir()
    file = sub_dir / "file.robot"
    file.touch()

    sub_dir1 = temp_project / "subdir1"
    sub_dir1.mkdir()
    subdir2 = sub_dir1 / "subdir2"
    subdir2.mkdir()
    file1 = subdir2 / "file.robot"
    file1.touch()

    root, discovery_by = find_project_root(file, subdir2, file)
    assert root == temp_project
    assert discovery_by == DiscoverdBy.ROBOT_TOML


@pytest.mark.parametrize(
    ("files"),
    {
        (),
        ("robot.toml",),
        ("pyproject.toml",),
        (".robot.toml",),
        ("pyproject.toml", "robot.toml"),
        ("robot.toml", ".robot.toml"),
        ("pyproject.toml", ".robot.toml"),
        ("pyproject.toml", "robot.toml", ".robot.toml"),
    },
)
def test_get_config_files_from_folder_should_work(temp_project: Path, files: Tuple[str, ...]) -> None:
    expected = []
    for file in files:
        robot_toml = temp_project / file
        robot_toml.touch()
        expected.append(robot_toml)

    result = get_config_files_from_folder(temp_project)
    assert [r[0] for r in result] == expected
