import os
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


def get_version() -> Version:
    if "npm_package_version" in os.environ:
        return Version(os.environ["npm_package_version"])
    else:
        return get_current_version_from_git()
