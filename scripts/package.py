import contextlib
import sys
from pathlib import Path
from subprocess import run

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
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    run(
        f"npx vsce package {'--pre-release' if get_version().prerelease else ''} -o ./dist", shell=True
    ).check_returncode()

    run("hatch -e build build", shell=True).check_returncode()


if __name__ == "__main__":
    main()
