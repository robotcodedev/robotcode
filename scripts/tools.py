import os
import subprocess
from pathlib import Path

from git.repo import Repo
from semantic_version import Version

# Dev builds of the VS Code extension get the patch number (C + 1) * VSCODE_DEV_BUILD_BLOCK + N,
# vscode-client/extension/index.ts recognizes them by it.
VSCODE_DEV_BUILD_BLOCK = 100000


def _run_commitizen(repo_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["cz", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _get_last_tag() -> tuple[Path, Version, int]:
    """Returns the repository path, the version of the last tag and the first-parent commits since that tag."""
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

    return repo_path, Version(current_version), int(commit_count)


def get_current_version_from_git() -> Version:
    repo_path, current_version, commit_count = _get_last_tag()

    if commit_count == 0:
        return current_version

    next_version = _run_commitizen(
        repo_path,
        "--no-raise",
        "NO_INCREMENT",
        "bump",
        "--get-next",
        "--devrelease",
        str(commit_count),
        "--yes",
    )
    if next_version:
        return Version(next_version)

    current_version.prerelease = ("dev", str(commit_count))
    return current_version


def get_vscode_dev_version() -> Version | None:
    """Returns the version of the VS Code extension for a commit after the last tag, None for a tagged commit.

    The VS Code Marketplace accepts only major.minor.patch, so the dev number goes into the patch number.
    """
    _, current_version, commit_count = _get_last_tag()

    if commit_count == 0:
        return None

    return Version(
        major=current_version.major,
        minor=current_version.minor,
        patch=(current_version.patch + 1) * VSCODE_DEV_BUILD_BLOCK + commit_count,
    )


def get_version() -> Version:
    if "npm_package_version" in os.environ:
        return Version(os.environ["npm_package_version"])
    if "CZ_PRE_NEW_VERSION" in os.environ:
        return Version(os.environ["CZ_PRE_NEW_VERSION"])

    return get_current_version_from_git()


if __name__ == "__main__":
    print(get_version())
