import os
from pathlib import Path
from subprocess import run

from git.repo import Repo
from semantic_version import Version


def get_current_version(repo: Repo) -> Version:
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

    repo = Repo(Path.cwd())

    current_version = get_current_version(repo)

    vsix_path = Path(dist_path, f"robotcode-{current_version}.vsix")

    run(["npx", "vsce", "publish", "-i", vsix_path], shell=True).check_returncode()
    run(["npx", "ovsx", "publish", vsix_path], shell=True).check_returncode()
    run(
        [
            "poetry",
            "publish",
            "--build",
            "--username",
            os.environ["PYPI_USERNAME"],
            "--password",
            os.environ["PYPI_PASSWORD"],
        ],
        shell=True,
    ).check_returncode()


if __name__ == "__main__":
    main()
