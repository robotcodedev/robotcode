import os
import subprocess
from pathlib import Path

from git.repo import Repo
from semantic_version import Version


def _run_commitizen(repo_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["cz", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_current_version_from_git() -> Version:
    repo = Repo(Path.cwd())
    if repo.bare or repo.working_tree_dir is None:
        raise ValueError("Not a valid Git repository with a working tree.")

    repo_path = Path(repo.working_tree_dir)
    current_version = _run_commitizen(repo_path, "version", "--project")
    current_tag = _run_commitizen(repo_path, "version", "--project", "--tag")
    commit_count = repo.git.rev_list(
        "--count",
        "--first-parent",
        f"{current_tag}..HEAD",
    )

    if commit_count == "0":
        return Version(current_version)

    next_version = _run_commitizen(
        repo_path,
        "--no-raise",
        "NO_INCREMENT",
        "bump",
        "--get-next",
        "--devrelease",
        commit_count,
        "--yes",
    )
    if next_version:
        return Version(next_version)

    version = Version(current_version)
    version.prerelease = ("dev", commit_count)
    return version


def get_version() -> Version:
    if "npm_package_version" in os.environ:
        return Version(os.environ["npm_package_version"])
    if "CZ_PRE_NEW_VERSION" in os.environ:
        return Version(os.environ["CZ_PRE_NEW_VERSION"])

    return get_current_version_from_git()


if __name__ == "__main__":
    print(get_version())
