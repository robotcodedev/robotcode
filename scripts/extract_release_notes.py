import contextlib
import re
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None or __package__ == "":
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from scripts.tools import get_version


def main() -> None:
    version = get_version()

    changelog = Path("CHANGELOG.md").read_text()

    regex = re.compile(rf"^\#\#\s*v({version})[^\n]*?\n(?P<text>.*?)^\#\#\s+", re.MULTILINE | re.DOTALL)

    for match in regex.finditer(changelog):
        print(match.group("text").strip())


if __name__ == "__main__":
    main()
