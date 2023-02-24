import contextlib
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
    preview = 1 if version.prerelease else 0

    print(preview)


if __name__ == "__main__":
    main()
