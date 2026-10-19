import argparse
import contextlib
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from semantic_version import Version

from scripts.publish import jetbrains_channel_versions, publish_jetbrains_plugin


def latest_successful_main_run() -> str:
    result = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            "build-test-package.yml",
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
        raise SystemExit("no successful run of build-test-package.yml for a push to main found")

    return run_id


def download_artifact(run_id: str, name: str, dist_path: Path) -> None:
    subprocess.run(
        ["gh", "run", "download", run_id, "--name", name, "--dir", str(dist_path)],
        check=True,
        timeout=600,
    )


def publish_jetbrains(dist_path: Path) -> None:
    run_id = latest_successful_main_run()
    print(f"downloading the JetBrains plugin of run {run_id}")
    download_artifact(run_id, "intellij-package", dist_path)

    plugin_paths = list(dist_path.glob("robotcode4ij-*.zip"))
    if len(plugin_paths) != 1:
        raise SystemExit(f"expected one JetBrains plugin in '{dist_path}', found {len(plugin_paths)}")

    version = Version(plugin_paths[0].name.removeprefix("robotcode4ij-").removesuffix(".zip"))

    if not version.prerelease:
        print(f"{version} is a release, its tag publishes it")
        return

    if str(version) in jetbrains_channel_versions("dev"):
        print(f"{version} is already in the channel dev")
        return

    publish_jetbrains_plugin(dist_path, version)


def is_pre_release_package(vsix_path: Path) -> bool:
    with zipfile.ZipFile(vsix_path) as vsix:
        manifest = ElementTree.fromstring(vsix.read("extension.vsixmanifest"))

    return any(
        element.get("Id") == "Microsoft.VisualStudio.Code.PreRelease" and element.get("Value") == "true"
        for element in manifest.iter()
    )


def publish_vscode(dist_path: Path) -> None:
    run_id = latest_successful_main_run()
    print(f"downloading the VS Code extension of run {run_id}")
    download_artifact(run_id, "vscode-package", dist_path)

    vsix_paths = list(dist_path.glob("robotcode-*.vsix"))
    if len(vsix_paths) != 1:
        raise SystemExit(f"expected one VS Code extension in '{dist_path}', found {len(vsix_paths)}")

    vsix_path = vsix_paths[0]

    if not is_pre_release_package(vsix_path):
        print(f"{vsix_path.name} is a release, its tag publishes it")
        return

    # the tokens come from the environment variables VSCE_PAT and OVSX_PAT
    failed = []
    for title, command in (
        (
            "VS Code Marketplace",
            ["npx", "vsce", "publish", "--packagePath", str(vsix_path), "--pre-release", "--skip-duplicate"],
        ),
        ("Open VSX", ["npx", "ovsx", "publish", str(vsix_path), "--skip-duplicate"]),
    ):
        print(f"running {title} upload")
        try:
            subprocess.run(command, check=True, timeout=600)
        except subprocess.SubprocessError as e:
            print(f"{title} upload failed: {e}", file=sys.stderr)
            failed.append(title)

    if failed:
        raise SystemExit(f"the upload to {' and '.join(failed)} failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish the latest successful build of main as a dev build.")
    parser.add_argument("target", choices=["jetbrains", "vscode"], help="the package to publish")
    args = parser.parse_args()

    dist_path = Path("./dist").absolute()

    if args.target == "jetbrains":
        publish_jetbrains(dist_path)
    else:
        publish_vscode(dist_path)


if __name__ == "__main__":
    main()
