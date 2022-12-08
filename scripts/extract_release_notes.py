import re
from pathlib import Path

from scripts.tools import get_version


def main() -> None:
    version = get_version()

    changelog = Path("CHANGELOG.md").read_text()

    regex = re.compile(rf"^\#\#\s*v({version})[^\n]*?\n(?P<text>.*?)^\#\#\s+", re.MULTILINE | re.DOTALL)

    for match in regex.finditer(changelog):
        print(match.group("text").strip())


if __name__ == "__main__":
    main()
