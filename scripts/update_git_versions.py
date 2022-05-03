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

    for f in ["robotcode/_version.py", "pyproject.toml"]:
        replace_in_file(
            Path(f),
            re.compile(r"""(^_*version_*\s*=\s*['"])([^'"]*)(['"])""", re.MULTILINE),
            rf"\g<1>{version or ''}{'.dev.0' if preview and version.prerelease is None else ''}\g<3>",
        )

    for f in ["package.json"]:
        replace_in_file(
            Path(f),
            re.compile(r"""(\"version\"\s*:\s*['"])([0-9]+\.[0-9]+\.[0-9]+.*)(['"])""", re.MULTILINE),
            rf"\g<1>{version or ''}{'.dev.0' if preview and version.prerelease is None else ''}\g<3>",
        )


if __name__ == "__main__":
    main()
