import os
import re
from pathlib import Path

from git.repo import Repo
from semantic_version import Version


def replace_in_file(filename: Path, pattern: "re.Pattern[str]", to: str) -> None:
    text = filename.read_text()
    new = pattern.sub(to, text)
    filename.write_text(new)


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

    preview = version.minor % 2 != 0

    for f in ["robotcode/_version.py", "pyproject.toml"]:
        replace_in_file(
            Path(f),
            re.compile(r"""(^_*version_*\s*=\s*['"])([^'"]*)(['"])""", re.MULTILINE),
            rf"\g<1>{version or ''}{'-preview' if preview else ''}\g<3>",
        )

    for f in ["CHANGELOG.md"]:
        replace_in_file(
            Path(f),
            re.compile(r"^(\#*\s*)(\[Unreleased\])$", re.MULTILINE),
            rf"\g<1>\g<2>{os.linesep}- none so far{os.linesep}\g<1> {version or ''}",
        )


if __name__ == "__main__":
    main()
