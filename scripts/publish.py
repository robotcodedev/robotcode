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

    run(f"npx vsce publish -i {vsix_path}", shell=True)
    run(f"npx ovsx publish {vsix_path}", shell=True)
    run(f"poetry publish --username {os.environ['PYPI_USERNAME']} --password {os.environ['PYPI_PASSWORD']}", shell=True)


if __name__ == "__main__":
    main()
