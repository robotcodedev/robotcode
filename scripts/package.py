from pathlib import Path
from subprocess import run

from scripts.tools import get_version


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    version = get_version()

    pre_release = version.minor % 2 != 0

    run(f"npx vsce package {'--pre-release' if pre_release else ''} -o ./dist", shell=True).check_returncode()

    run("poetry build", shell=True).check_returncode()


if __name__ == "__main__":
    main()
