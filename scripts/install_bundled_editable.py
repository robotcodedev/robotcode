import shutil
from pathlib import Path
from subprocess import run


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    shutil.rmtree("./bundled/libs", ignore_errors=True)

    run(
        "pip --disable-pip-version-check install -U -t ./bundled/libs --no-cache-dir --implementation py "
        "--only-binary=:all: --no-binary=:none: -r ./bundled_requirements.txt",
        shell=True,
    ).check_returncode()

    packages = [f"-e {path}" for path in Path("./packages").iterdir() if (path / "pyproject.toml").exists()]

    run(
        "pip --disable-pip-version-check "
        f"install -U -t ./bundled/libs --no-cache-dir --implementation py --no-deps {' '.join(packages)} -e .",
        shell=True,
    ).check_returncode()


if __name__ == "__main__":
    main()
