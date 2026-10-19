import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from packaging.version import Version as PackageVersion
from semantic_version import Version

from scripts.publish import jetbrains_channel_versions, publish_jetbrains_plugin

# how long and how often the latest build of main is waited for, builds took up to 110 minutes
LATEST_RUN_WAIT_SECONDS = 2 * 60 * 60
LATEST_RUN_POLL_SECONDS = 60


def gh_json(*args: str) -> Any:
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True, timeout=120)
    return json.loads(result.stdout)


def find_latest_run() -> None:
    """Hands on the id of the latest build of main through GITHUB_OUTPUT, if that build succeeded.

    An older successful build is never taken: during work on a feature, the latest build is often broken and the
    one before it an unfinished state.
    """
    runs = gh_json(
        "run",
        "list",
        "--workflow",
        "build-test-package.yml",
        "--branch",
        "main",
        "--event",
        "push",
        "--limit",
        "1",
        "--json",
        "databaseId,status,conclusion",
    )
    if not runs:
        print("no run of build-test-package.yml for a push to main, so there is no dev build")
        return

    run = runs[0]
    run_id = str(run["databaseId"])
    deadline = time.monotonic() + LATEST_RUN_WAIT_SECONDS

    while run["status"] != "completed":
        if time.monotonic() >= deadline:
            print(f"the latest run {run_id} on main isn't done in time, so there is no dev build")
            return
        print(f"waiting for the latest run {run_id} on main, which is {run['status']}")
        time.sleep(LATEST_RUN_POLL_SECONDS)
        run = gh_json("run", "view", run_id, "--json", "status,conclusion")

    if run["conclusion"] != "success":
        print(f"the latest run {run_id} on main ended with '{run['conclusion']}', so there is no dev build")
        return

    print(f"the latest run {run_id} on main succeeded")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"run-id={run_id}\n")


def download_artifact(run_id: str, name: str, dist_path: Path) -> None:
    subprocess.run(
        ["gh", "run", "download", run_id, "--name", name, "--dir", str(dist_path)],
        check=True,
        timeout=600,
    )


def publish_jetbrains(run_id: str, dist_path: Path) -> None:
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


def publish_vscode(run_id: str, dist_path: Path) -> None:
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


def pypi_has_version(project: str, version: str) -> bool:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{project}/{version}/json", timeout=60):
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def publish_python(run_id: str, dist_path: Path) -> None:
    print(f"downloading the Python packages of run {run_id}")
    download_artifact(run_id, "python-packages", dist_path)
    download_artifact(run_id, "wheel-packages", dist_path)

    root_wheels = list(dist_path.glob("robotcode-*-py3-none-any.whl"))
    if len(root_wheels) != 1:
        raise SystemExit(f"expected one wheel of robotcode in '{dist_path}', found {len(root_wheels)}")

    version = PackageVersion(root_wheels[0].name.removeprefix("robotcode-").removesuffix("-py3-none-any.whl"))

    if not version.is_prerelease:
        print(f"{version} is a release, its tag publishes it")
        return

    # robotcode is uploaded last, so PyPI has the whole version when it has robotcode
    if pypi_has_version("robotcode", str(version)):
        print(f"{version} is already on PyPI")
        return

    # the packages robotcode requires first, so that PyPI never has a dev version of robotcode without them
    packages = sorted([*dist_path.glob("robotcode_*.whl"), *dist_path.glob("robotcode_*.tar.gz")])
    if not packages:
        # without files, hatch publish would upload all of dist/, robotcode included
        raise SystemExit(f"found none of the packages that robotcode requires in '{dist_path}'")
    uploads = [packages, sorted([*dist_path.glob("robotcode-*.whl"), *dist_path.glob("robotcode-*.tar.gz")])]
    # the credentials come from the environment, so they are not part of a command that an error shows
    env = {
        **os.environ,
        "HATCH_INDEX_USER": os.environ.get("PYPI_USERNAME", ""),
        "HATCH_INDEX_AUTH": os.environ.get("PYPI_PASSWORD", ""),
    }
    try:
        for files in uploads:
            print(f"running PyPI upload of {len(files)} files")
            subprocess.run(
                ["hatch", "-e", "build", "publish", "--no-prompt", *map(str, files)],
                check=True,
                timeout=600,
                env=env,
            )
    except subprocess.SubprocessError as e:
        raise SystemExit(f"the upload to PyPI failed: {e}") from e


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish the latest successful build of main as a dev build.")
    parser.add_argument(
        "target",
        choices=["latest-run", "jetbrains", "vscode", "python"],
        help="latest-run finds the build to publish, the others publish its packages",
    )
    parser.add_argument("--run-id", help="the build whose packages to publish, as latest-run hands it on")
    args = parser.parse_args()

    if args.target == "latest-run":
        find_latest_run()
        return

    if not args.run_id:
        parser.error(f"the target {args.target} needs --run-id")

    dist_path = Path("./dist").absolute()

    if args.target == "jetbrains":
        publish_jetbrains(args.run_id, dist_path)
    elif args.target == "vscode":
        publish_vscode(args.run_id, dist_path)
    else:
        publish_python(args.run_id, dist_path)


if __name__ == "__main__":
    main()
