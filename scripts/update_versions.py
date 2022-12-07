import os
import re
from pathlib import Path

from scripts.tools import get_version


def replace_in_file(filename: Path, pattern: "re.Pattern[str]", to: str) -> None:
    text = filename.read_text()
    new = pattern.sub(to, text)
    filename.write_text(new)


def main() -> None:

    version = get_version()

    preview = version.minor % 2 != 0

    for f in ["robotcode/__version__.py", "pyproject.toml"]:
        replace_in_file(
            Path(f),
            re.compile(r"""(^_*version_*\s*=\s*['"])([^'"]*)(['"])""", re.MULTILINE),
            rf"\g<1>{version or ''}{'.dev.0' if preview and version.prerelease is None else ''}\g<3>",
        )

    for f in ["CHANGELOG.md"]:
        replace_in_file(
            Path(f),
            re.compile(r"^(\#*\s*)(\[Unreleased\])$", re.MULTILINE),
            rf"\g<1>\g<2>{os.linesep}- none so far{os.linesep}\g<1> {version or ''}",
        )


if __name__ == "__main__":
    main()
