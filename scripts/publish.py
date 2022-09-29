import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.tools import get_version


def run(title: str, *args: Any, **kwargs: Any) -> None:
    try:
        print(f"running {title}")
        subprocess.run(*args, **kwargs)
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException as e:
        print(f"{title} failed: {e}", file=sys.stderr)
        pass


def main() -> None:
    dist_path = Path("./dist")

    if not dist_path.exists():
        raise FileNotFoundError(f"dist folder '{dist_path}' not exists")

    current_version = get_version()

    vsix_path = Path(dist_path, f"robotcode-{current_version}.vsix")

    run("npx vsce publish", f"npx vsce publish -i {vsix_path}", shell=True, timeout=600)
    run("npx ovsx publish", f"npx ovsx publish {vsix_path}", shell=True, timeout=600)
    run(
        "poetry publish",
        f"poetry publish --username {os.environ['PYPI_USERNAME']} --password {os.environ['PYPI_PASSWORD']}",
        shell=True,
        timeout=600,
    )


if __name__ == "__main__":
    main()
