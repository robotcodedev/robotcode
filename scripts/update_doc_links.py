import re
from pathlib import Path

from scripts.tools import get_version


def replace_in_file(filename: Path, pattern: "re.Pattern[str]", to: str) -> None:
    text = filename.read_text()

    new = pattern.sub(to, text)
    filename.write_text(new)


REPOSITORY_BASE = "https://raw.githubusercontent.com/d-biehl/robotcode"


def main() -> None:
    version = get_version()
    if version.prerelease:
        tag_base = f"{REPOSITORY_BASE}/v{version}"

        replace_in_file(
            Path("README.md"),
            re.compile(r"(\!\[.*?\]\()(\.)(/[^\)]*?)(\))"),
            rf"""\g<1>{tag_base}\g<3>\g<4>""",
        )
        replace_in_file(
            Path("CHANGELOG.md"),
            re.compile(r"(\!\[.*?\]\()(\.)(/[^\)]*?)(\))"),
            rf"""\g<1>{tag_base}\g<3>\g<4>""",
        )


if __name__ == "__main__":
    main()
