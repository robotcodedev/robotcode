import os
from pathlib import Path
from typing import NamedTuple, Optional

from git.repo import Repo
from semantic_version import Version


class GitDescribeVersion(NamedTuple):
    version: str
    commits: Optional[str] = None
    hash: Optional[str] = None


def get_current_version_from_git() -> Version:
    repo = Repo(Path.cwd())

    git_version = GitDescribeVersion(*repo.git.describe("--long", "--first-parent", "--match", "v[0-9]*").split("-"))
    version = Version(git_version.version[1:])
    if git_version.commits is not None:
        version = version.next_patch()
        version.prerelease = ("dev", git_version.commits)
    return version


def get_version() -> Version:
    if "npm_package_version" in os.environ:
        return Version(os.environ["npm_package_version"])
    else:
        return get_current_version_from_git()
