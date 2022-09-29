import os
from pathlib import Path
from subprocess import run

from scripts.tools import get_version


def main() -> None:
    dist_path = Path("./dist")

    if not dist_path.exists():
        raise FileNotFoundError(f"dist folder '{dist_path}' not exists")

    current_version = get_version()

    vsix_path = Path(dist_path, f"robotcode-{current_version}.vsix")

    print("publish to vscode marketplace...")
    run(f"npx vsce publish -i {vsix_path}", shell=True, timeout=600)

    print("publish to openVSX...")
    run(f"npx ovsx publish {vsix_path}", shell=True, timeout=600)

    print("publish to PyPi...")
    run(
        f"poetry publish --username {os.environ['PYPI_USERNAME']} --password {os.environ['PYPI_PASSWORD']}",
        shell=True,
        timeout=600,
    )


if __name__ == "__main__":
    main()
