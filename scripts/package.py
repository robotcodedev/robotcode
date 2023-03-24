import contextlib
import shutil
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
    dist_path = Path("./dist").absolute()
    if not dist_path.exists():
        dist_path.mkdir()

    packages = [f"{path}" for path in Path("./packages").iterdir() if (path / "pyproject.toml").exists()]
    for package in packages:
        run(f"hatch -e build build {dist_path}", shell=True, cwd=package).check_returncode()

    run(f"hatch -e build build {dist_path}", shell=True).check_returncode()

    shutil.rmtree("./bundled/libs", ignore_errors=True)

    run(
        "pip --disable-pip-version-check install -U -t ./bundled/libs --no-cache-dir --implementation py "
        "--only-binary=:all: --no-binary=:none: -r ./bundled_requirements.txt",
        shell=True,
    ).check_returncode()

    run(
        "pip --disable-pip-version-check "
        f"install -U -t ./bundled/libs --no-cache-dir --implementation py --no-deps {' '.join(packages)} .",
        shell=True,
    ).check_returncode()

    run(
        f"npx vsce package {'--pre-release' if get_version().prerelease else ''} -o ./dist", shell=True
    ).check_returncode()


if __name__ == "__main__":
    main()
