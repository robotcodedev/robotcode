import shutil
from pathlib import Path
from subprocess import run


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    shutil.rmtree("./bundled/libs", ignore_errors=True)

    run(
        "pip install -U -t ./bundled/libs --no-cache-dir --implementation py --no-deps -e .", shell=True
    ).check_returncode()


if __name__ == "__main__":
    main()
