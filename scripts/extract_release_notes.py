import os
import re
from pathlib import Path

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
    if "npm_package_version" in os.environ:
        version = Version(os.environ["npm_package_version"])
    else:
        version = get_current_version_from_git()

    changelog = Path("CHANGELOG.md").read_text()

    regex = re.compile(rf"^\#\#\s*({version})(?P<text>.*?)^\#\#\s+", re.MULTILINE | re.DOTALL)

    for match in regex.finditer(changelog):
        print(match.group("text").strip())


if __name__ == "__main__":
    main()
