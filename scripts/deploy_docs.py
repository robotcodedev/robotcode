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


from scripts.tools import get_current_version_from_git


def main() -> None:
    version = get_current_version_from_git()
    alias = "latest"

    if version.prerelease:
        version = version.next_minor()
        alias = "dev"

    version.major, version.minor

    run(
        "mike deploy --push --update-aliases --rebase --force "
        f'--title "v{version.major}.{version.minor}.x ({alias})" {version.major}.{version.minor} {alias}',
        shell=True,
    ).check_returncode()


if __name__ == "__main__":
    main()
