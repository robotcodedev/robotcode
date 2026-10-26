#!/usr/bin/env python3
"""Release the bundled robotcode agent plugin together with a RobotCode release.

Every RobotCode release tags the plugin commit recorded in
``chat-plugins/.upstream.json`` as ``robotcode--vX.Y.Z`` in
robotframework-agent-plugins and moves that repository's ``main`` to it.

Subcommands:
    check             before the bump: the vendored plugin is ready for the release
    prepare           after the bump: tag the recorded commit and fast-forward main
                      in the local plugin checkout, without pushing
    verify-published  in the publish job: the tag and main are on GitHub

Prereleases are left out by ``check`` and ``prepare``.

Examples:
    python scripts/chat_plugin_release.py check 2.9.0
    python scripts/chat_plugin_release.py prepare 2.9.0 --source ../robotframework-agent-plugins
    python scripts/chat_plugin_release.py verify-published 2.9.0
"""

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from semantic_version import Version

from scripts.sync_chat_plugin import DEFAULT_SOURCE, DEST, PLUGIN_SUBPATH, STAMP, equal_trees, git

DEFAULT_REMOTE = "https://github.com/robotcodedev/robotframework-agent-plugins.git"
PLUGIN_JSON = Path(".plugin") / "plugin.json"
SKILL_MD = Path("skills") / "robotcode" / "SKILL.md"
SKILL_VERSION = re.compile(r"^metadata:[ \t]*\n(?:[ \t]+.*\n)*?[ \t]+version:[ \t]*[\"']?([^\"'\s]+)", re.MULTILINE)


def die(msg: str) -> NoReturn:
    print(f"chat-plugin-release: {msg}", file=sys.stderr)
    sys.exit(1)


def git_succeeds(cwd: Path, *args: str) -> bool:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True).returncode == 0


def rev(cwd: Path, ref: str) -> str | None:
    result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ref], cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def read_version(value: str | None, env: str | None = None) -> Version:
    text = value or (os.environ.get(env) if env else None)
    if not text:
        die(f"no version given; pass it as argument or set {env}" if env else "no version given")
    try:
        return Version(text)
    except ValueError:
        die(f"{text} is not a SemVer version")


def recorded_sha() -> str:
    return str(json.loads(STAMP.read_text(encoding="utf-8"))["sha"])


def plugin_checkout(source: Path) -> Path:
    root = source.resolve()
    if not (root / ".plugin" / "marketplace.json").is_file() or not (root / PLUGIN_SUBPATH).is_dir():
        die(f"no checkout of the plugin repository at {root}; clone {DEFAULT_REMOTE} there or pass --source <path>")
    return root


def check(version: Version, source: Path) -> int:
    if version.prerelease:
        print(f"{version} is a prerelease, the agent plugin is not checked")
        return 0

    root = plugin_checkout(source)
    sha = recorded_sha()
    problems: list[str] = []

    plugin_version = json.loads((DEST / PLUGIN_JSON).read_text(encoding="utf-8")).get("version")
    match = SKILL_VERSION.search((DEST / SKILL_MD).read_text(encoding="utf-8"))
    skill_version = match.group(1) if match else None
    if plugin_version != str(version) or skill_version != str(version):
        problems.append(
            f"the vendored plugin has the version {plugin_version} in plugin.json and {skill_version} in SKILL.md, "
            f"not {version}: on the plugin repository's next, set `version` in {PLUGIN_SUBPATH / PLUGIN_JSON} and "
            f"`metadata.version` in {PLUGIN_SUBPATH / SKILL_MD} to {version}, run `python scripts/sync_manifests.py` "
            "and commit, then run `hatch run build:sync-chat-plugin` here and commit the result"
        )

    if not equal_trees(root / PLUGIN_SUBPATH, DEST):
        problems.append(
            f"chat-plugins/robotcode/ is out of sync with {root / PLUGIN_SUBPATH}: "
            "run `hatch run build:sync-chat-plugin` and commit the result"
        )

    if rev(root, "refs/heads/next") is None:
        problems.append(f"{root} has no local branch next: create it from origin/next")
    elif not git_succeeds(root, "merge-base", "--is-ancestor", sha, "refs/heads/next"):
        problems.append(
            f"the commit {sha[:7]} recorded in chat-plugins/.upstream.json is not on the branch next of {root}: "
            "check out next there, run `hatch run build:sync-chat-plugin` here and commit the result"
        )

    if problems:
        die(f"the agent plugin is not ready for the release {version}:\n" + "\n".join(f"  - {p}" for p in problems))

    print(f"the agent plugin is ready for the release {version} (commit {sha[:7]} on next)")
    return 0


def prepare(version: Version, source: Path) -> int:
    if version.prerelease:
        print(f"{version} is a prerelease, no agent plugin release is prepared")
        return 0

    root = plugin_checkout(source)
    sha = recorded_sha()
    tag = f"robotcode--v{version}"
    rerun = f"rerun `hatch run build:prepare-chat-plugin-release {version}` afterwards"

    if not git_succeeds(root, "cat-file", "-e", f"{sha}^{{commit}}"):
        die(f"the recorded commit {sha[:7]} is not in {root}: fetch the plugin repository and {rerun}")

    tag_sha = rev(root, f"refs/tags/{tag}^{{commit}}")
    if tag_sha is not None and tag_sha != sha:
        die(f"the tag {tag} in {root} points to {tag_sha[:7]}, not to the recorded commit {sha[:7]}")

    main_sha = rev(root, "refs/heads/main")
    if main_sha is None:
        die(f"{root} has no local branch main: create it from origin/main and {rerun}")
    if main_sha != sha and not git_succeeds(root, "merge-base", "--is-ancestor", main_sha, sha):
        die(f"main of {root} is on {main_sha[:7]}, which the recorded commit {sha[:7]} doesn't contain")

    if tag_sha is None:
        # signed when the git configuration signs tags (tag.gpgSign)
        git(root, "tag", "-a", tag, sha, "-m", f"robotcode plugin for RobotCode {version}")
        print(f"created the tag {tag} on {sha[:7]}")
    else:
        print(f"the tag {tag} is already on {sha[:7]}")

    if main_sha == sha:
        print(f"main is already on {sha[:7]}")
    else:
        branch = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=root, capture_output=True, text=True
        ).stdout.strip()
        if branch == "main":
            git(root, "merge", "--ff-only", sha)
        else:
            git(root, "update-ref", "refs/heads/main", sha, main_sha)
        print(f"fast-forwarded main from {main_sha[:7]} to {sha[:7]}")

    print(f"push the plugin release together with RobotCode {version}:\n  git -C {root} push origin main {tag}")
    return 0


def verify_published(version: Version, remote: str) -> int:
    sha = recorded_sha()
    tag = f"robotcode--v{version}"

    # an annotated tag lists its commit as <tag>^{} only when that is asked for, too
    refs: dict[str, str] = {}
    for line in subprocess.check_output(
        ["git", "ls-remote", remote, "refs/heads/main", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"], text=True
    ).splitlines():
        ref_sha, ref = line.split("\t", 1)
        refs[ref] = ref_sha

    tag_sha = refs.get(f"refs/tags/{tag}^{{}}", refs.get(f"refs/tags/{tag}"))
    main_sha = refs.get("refs/heads/main")

    problems: list[str] = []
    if tag_sha is None:
        problems.append(f"the tag {tag} is missing")
    elif tag_sha != sha:
        problems.append(f"the tag {tag} points to {tag_sha[:7]}, not to the recorded commit {sha[:7]}")
    if main_sha != sha:
        problems.append(f"main is on {main_sha[:7] if main_sha else 'nothing'}, not on the recorded commit {sha[:7]}")

    if problems:
        die(
            f"the agent plugin release for {version} is not published in {remote}:\n"
            + "\n".join(f"  - {p}" for p in problems)
            + f"\npush the plugin repository (`git push origin main {tag}`) before re-running this job"
        )

    print(f"the agent plugin release {tag} is published on {sha[:7]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = ap.add_subparsers(dest="command", required=True)

    source_help = f"Path to a local clone of the plugin repository (default: {DEFAULT_SOURCE})."

    check_ap = commands.add_parser("check", help="Check that the vendored plugin is ready for a release.")
    check_ap.add_argument("version", nargs="?", help="The new version (default: $CZ_PRE_NEW_VERSION).")
    check_ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help=source_help)

    prepare_ap = commands.add_parser(
        "prepare", help="Tag the recorded commit and fast-forward main in the local plugin checkout."
    )
    prepare_ap.add_argument("version", nargs="?", help="The released version (default: $CZ_POST_CURRENT_VERSION).")
    prepare_ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help=source_help)

    verify_ap = commands.add_parser(
        "verify-published", help="Check that the tag and main of the plugin release are in the public repository."
    )
    verify_ap.add_argument("version", help="The released version.")
    verify_ap.add_argument(
        "--remote", default=DEFAULT_REMOTE, help=f"The plugin repository (default: {DEFAULT_REMOTE})."
    )

    args = ap.parse_args()
    try:
        if args.command == "check":
            return check(read_version(args.version, "CZ_PRE_NEW_VERSION"), args.source)
        if args.command == "prepare":
            return prepare(read_version(args.version, "CZ_POST_CURRENT_VERSION"), args.source)
        return verify_published(read_version(args.version), args.remote)
    except subprocess.CalledProcessError as e:
        die(f"`{' '.join(e.cmd)}` failed with exit code {e.returncode}")


if __name__ == "__main__":
    sys.exit(main())
