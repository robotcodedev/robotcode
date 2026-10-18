"""Tests that `iter_files_includes` decides for one file as `iter_files` does for all of them."""

from pathlib import Path
from typing import Dict

import pytest

from robotcode.core.ignore_spec import (
    DEFAULT_SPEC_RULES,
    GIT_IGNORE_FILE,
    ROBOT_IGNORE_FILE,
    IgnoreSpec,
    iter_files,
    iter_files_includes,
)

TREE: Dict[str, str] = {
    "a.robot": "",
    "scratch.robot": "",
    "excluded/b.robot": "",
    ".hidden/c.robot": "",
    ".hidden.robot": "",
    # a .gitignore applies to its folder
    "git/.gitignore": "ignored.robot\nbuild/\n",
    "git/ignored.robot": "",
    "git/kept.robot": "",
    "git/build/d.robot": "",
    # a folder uses the first ignore file name that exists in it, and the folders below it use only that name
    "both/.robotignore": "by_robotignore.robot\n",
    "both/.gitignore": "by_gitignore.robot\n",
    "both/by_robotignore.robot": "",
    "both/by_gitignore.robot": "",
    "both/sub/.gitignore": "e.robot\n",
    "both/sub/e.robot": "",
    "both/sub/.robotignore": "f.robot\n",
    "both/sub/f.robot": "",
    # a pattern of an outer ignore file applies below it
    "nested/deep/scratch.robot": "",
}


@pytest.mark.parametrize("include_hidden", [False, True], ids=["without hidden", "with hidden"])
@pytest.mark.parametrize("root_ignore", [None, "scratch.robot\n"], ids=["no root ignore file", "root .gitignore"])
def test_decides_like_iter_files(tmp_path: Path, include_hidden: bool, root_ignore: str) -> None:
    files = dict(TREE)
    if root_ignore is not None:
        files[".gitignore"] = root_ignore
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")

    ignore_files = [ROBOT_IGNORE_FILE, GIT_IGNORE_FILE]
    spec = IgnoreSpec.from_list([*DEFAULT_SPEC_RULES, "excluded/"], tmp_path)

    expected = set(iter_files(tmp_path, ignore_files=ignore_files, include_hidden=include_hidden, parent_spec=spec))
    decided = {
        path
        for path in tmp_path.rglob("*")
        if iter_files_includes(
            path, tmp_path, ignore_files=ignore_files, include_hidden=include_hidden, parent_spec=spec
        )
    }

    assert decided == expected


def test_a_file_outside_the_root_is_not_included(tmp_path: Path) -> None:
    (tmp_path / "root").mkdir()
    (tmp_path / "outside.robot").write_text("", encoding="utf-8")

    assert not iter_files_includes(tmp_path / "outside.robot", tmp_path / "root")


def test_a_missing_file_is_not_included(tmp_path: Path) -> None:
    assert not iter_files_includes(tmp_path / "missing.robot", tmp_path)
