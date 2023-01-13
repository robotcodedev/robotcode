from pathlib import Path
from subprocess import run

from scripts.tools import get_version


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    run(
        f"npx vsce package {'--pre-release' if get_version().prerelease else ''} -o ./dist", shell=True
    ).check_returncode()

    run("poetry build", shell=True).check_returncode()


if __name__ == "__main__":
    main()
