import contextlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from semantic_version import Version

from scripts.publish import publish_jetbrains_plugin


def latest_successful_main_run() -> str:
    result = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            "build-test-package-publish.yml",
            "--branch",
            "main",
            "--event",
            "push",
            "--status",
            "success",
            "--limit",
            "1",
            "--json",
            "databaseId",
            "--jq",
            ".[].databaseId",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    run_id = result.stdout.strip()

    if not run_id:
        raise SystemExit("no successful run of build-test-package-publish.yml for a push to main found")

    return run_id


def dev_channel_versions() -> set[str]:
    with urllib.request.urlopen(
        "https://plugins.jetbrains.com/api/plugins/26216/updates?channel=dev&size=100", timeout=60
    ) as response:
        return {update["version"] for update in json.load(response)}


def main() -> None:
    dist_path = Path("./dist").absolute()

    run_id = latest_successful_main_run()
    print(f"downloading the JetBrains plugin of run {run_id}")
    subprocess.run(
        ["gh", "run", "download", run_id, "--name", "intellij-package", "--dir", str(dist_path)],
        check=True,
        timeout=600,
    )

    plugin_paths = list(dist_path.glob("robotcode4ij-*.zip"))
    if len(plugin_paths) != 1:
        raise SystemExit(f"expected one JetBrains plugin in '{dist_path}', found {len(plugin_paths)}")

    version = Version(plugin_paths[0].name.removeprefix("robotcode4ij-").removesuffix(".zip"))

    if not version.prerelease:
        print(f"{version} is a release, its tag publishes it")
        return

    if str(version) in dev_channel_versions():
        print(f"{version} is already in the channel dev")
        return

    publish_jetbrains_plugin(dist_path, version)


if __name__ == "__main__":
    main()
