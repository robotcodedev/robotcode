import os
from pathlib import Path
from subprocess import run


def main() -> None:
    dist_path = Path("./dist")
    if not dist_path.exists():
        dist_path.mkdir()

    uv_path = os.environ.get("HATCH_UV", None)
    if uv_path:
        uv_path = f'"{uv_path}"'

    installer_command = f"{uv_path+' ' if uv_path else ''}pip {'' if uv_path else '--disable-pip-version-check'}"

    run(
        f"{installer_command} install -U -r ./bundled_requirements.txt",
        shell=True,
        check=False,
    ).check_returncode()

    packages = [f"-e {path}" for path in Path("./packages").iterdir() if (path / "pyproject.toml").exists()]

    run(
        f"{installer_command} install --no-deps -U {' '.join(packages)}",
        shell=True,
        check=False,
    ).check_returncode()


if __name__ == "__main__":
    main()
