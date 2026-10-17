import contextlib
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

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


def run(title: str, *args: Any, **kwargs: Any) -> None:
    try:
        print(f"running {title}")
        subprocess.run(*args, **kwargs)
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException as e:
        print(f"{title} failed: {e}", file=sys.stderr)


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

    if not version.prerelease:
        run(
            "npx vsce publish",
            f"npx vsce publish -i {vsix_path}",
            shell=True,
            timeout=600,
        )
    run(
        "npx ovsx publish",
        f"npx ovsx publish {vsix_path}",
        shell=True,
        timeout=600,
    )

    run(
        "hatch publish",
        f'hatch -e build publish -u "{os.environ["PYPI_USERNAME"]}" -a "{os.environ["PYPI_PASSWORD"]}"',
        shell=True,
        timeout=600,
    )

    publish_jetbrains_plugin(dist_path, version)


if __name__ == "__main__":
    main()
