import contextlib
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from semantic_version import Version

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from scripts.tools import get_version


def run_upload(store: str, command: List[str], env: Optional[Dict[str, str]] = None) -> None:
    print(f"running {store} upload")
    subprocess.run(command, check=True, timeout=600, env=env)


def publish_jetbrains_plugin(dist_path: Path, version: Version) -> None:
    plugin_path = Path(dist_path, f"robotcode4ij-{version}.zip")

    if not plugin_path.exists():
        raise FileNotFoundError(f"JetBrains plugin '{plugin_path}' not found")

    channel = "dev" if version.prerelease else ""

    print("running JetBrains Marketplace upload")
    # the shell expands the token, so it is not part of the command that an error shows
    subprocess.run(
        'curl --fail-with-body --silent --show-error --header "Authorization: Bearer $PUBLISH_TOKEN"'
        f" --form xmlId=dev.robotcode.robotcode4ij --form {shlex.quote(f'file=@{plugin_path}')}"
        f" --form channel={channel} https://plugins.jetbrains.com/api/updates/upload",
        shell=True,
        check=True,
        timeout=600,
    )


def main() -> None:
    dist_path = Path("./dist").absolute()

    if not dist_path.exists():
        raise FileNotFoundError(f"dist folder '{dist_path}' not exists")

    version = get_version()

    vsix_path = Path(dist_path, f"robotcode-{version}.vsix")

    # the tokens come from the environment, so they are not part of a command that an error shows
    pypi_env = {
        **os.environ,
        "HATCH_INDEX_USER": os.environ.get("PYPI_USERNAME", ""),
        "HATCH_INDEX_AUTH": os.environ.get("PYPI_PASSWORD", ""),
    }

    uploads: List[Tuple[str, Callable[[], None]]] = []
    if not version.prerelease:
        uploads.append(
            (
                "VS Code Marketplace",
                lambda: run_upload("VS Code Marketplace", ["npx", "vsce", "publish", "-i", str(vsix_path)]),
            )
        )
    uploads.append(("Open VSX", lambda: run_upload("Open VSX", ["npx", "ovsx", "publish", str(vsix_path)])))
    uploads.append(("PyPI", lambda: run_upload("PyPI", ["hatch", "-e", "build", "publish", "--no-prompt"], pypi_env)))
    uploads.append(("JetBrains Marketplace", lambda: publish_jetbrains_plugin(dist_path, version)))

    # a failed upload must not keep the release from the other stores
    failed = []
    for store, upload in uploads:
        try:
            upload()
        except (subprocess.SubprocessError, OSError) as e:
            print(f"{store} upload failed: {e}", file=sys.stderr)
            failed.append(store)

    if failed:
        raise SystemExit(f"the upload to {' and '.join(failed)} failed")


if __name__ == "__main__":
    main()
