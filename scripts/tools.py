import os
import re
from pathlib import Path
from typing import NamedTuple, Optional

from git.repo import Repo
from semantic_version import Version


class GitDescribeVersion(NamedTuple):
    version: str
    commits: Optional[str] = None
    hash: Optional[str] = None


def determine_version_bump(repo_path="."):
    try:
        repo = Repo(repo_path)
        if repo.bare:
            raise ValueError("Not a valid Git repository.")

        tags = sorted(repo.tags, key=lambda t: t.commit.committed_date, reverse=True)
        version_tags = [tag for tag in tags if tag.name.startswith("v")]
        if not version_tags:
            raise ValueError("No version tags found.")

        last_tag = version_tags[0]
        commits = repo.iter_commits(f"{last_tag.name}..HEAD")

        ignored_types = ["chore", "style", "refactor", "test"]
        patch_types = ["fix", "docs", "perf"]

        minor_change = False
        patch_change = False

        for commit in commits:
            message = commit.message.strip()

            if any(re.match(rf"^{ignored_type}(\([^\)]+\))?:", message) for ignored_type in ignored_types):
                continue

            if "BREAKING CHANGE:" in message or re.match(r"^feat(\([^\)]+\))?!:", message):
                return "major"

            if re.match(r"^feat(\([^\)]+\))?:", message):
                minor_change = True

            if any(re.match(rf"^{patch_types}(\([^\)]+\))?:", message) for ignored_type in ignored_types):
                patch_change = True

        if minor_change:
            return "minor"
        if patch_change:
            return "patch"
        return None

    except Exception as e:
        raise RuntimeError(f"Error: {e}")


def get_current_version_from_git() -> Version:
    repo = Repo(Path.cwd())

    git_version = GitDescribeVersion(
        *repo.git.describe("--tag", "--long", "--first-parent", "--match", "v[0-9]*").rsplit("-", 2)
    )

    version = Version(git_version.version[1:])
    if git_version.commits is not None and git_version.commits != "0":
        next_version = determine_version_bump()
        if next_version == "major":
            version = version.next_major()
        elif next_version == "minor":
            version = version.next_minor()
        elif next_version == "patch":
            version = version.next_patch()
        version.prerelease = ("dev", git_version.commits)

    return version


def get_version() -> Version:
    if "npm_package_version" in os.environ:
        return Version(os.environ["npm_package_version"])
    if "CZ_PRE_NEW_VERSION" in os.environ:
        return Version(os.environ["CZ_PRE_NEW_VERSION"])

    return get_current_version_from_git()


if __name__ == "__main__":
    print(get_version())
