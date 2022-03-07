import os
from pathlib import Path
from subprocess import run

from git.repo import Repo
from semantic_version import Version


def get_current_version_from_git() -> Version:
    repo = Repo(Path.cwd())

    result = None
    for tag in repo.tags:
        v = tag.name
        if v.startswith("v."):
            v = v[2:]
        elif v.startswith("v"):
            v = v[1:]

        try:
            v = Version(v)
        except ValueError:
            continue

        if not result or v > result:
            result = v

    return result


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    if "npm_package_version" in os.environ:
        current_version = Version(os.environ["npm_package_version"])
    else:
        current_version = get_current_version_from_git()

    pre_release = current_version.minor % 2 != 0

    run(
        ["npx", "vsce", "package", *(["--pre-release"] if pre_release else []), "-o", "./dist"], shell=True
    ).check_returncode()

    run(
        [
            "poetry",
            "build",
        ],
        shell=True,
    ).check_returncode()


if __name__ == "__main__":
    main()
