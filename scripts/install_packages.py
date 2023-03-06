from pathlib import Path
from subprocess import run


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    packages = [f"-e {path}" for path in Path("./packages").iterdir() if (path / "pyproject.toml").exists()]

    run(
        f"pip install -U {' '.join(packages)}",
        shell=True,
    ).check_returncode()


if __name__ == "__main__":
    main()
