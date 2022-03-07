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
        raise FileNotFoundError(f"dist folder '{dist_path}' not exists")

    if "npm_package_version" in os.environ:
        current_version = Version(os.environ["npm_package_version"])
    else:
        current_version = get_current_version_from_git()

    vsix_path = Path(dist_path, f"robotcode-{current_version}.vsix")

    run(["npx", "vsce", "publish", "-i", vsix_path], shell=True).check_returncode()
    run(["npx", "ovsx", "publish", vsix_path], shell=True).check_returncode()
    run(
        [
            "poetry",
            "publish",
            "--username",
            os.environ["PYPI_USERNAME"],
            "--password",
            os.environ["PYPI_PASSWORD"],
        ],
        shell=True,
    ).check_returncode()


if __name__ == "__main__":
    main()
