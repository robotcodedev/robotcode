#!/usr/bin/env python3
"""Sync the robotcode chat-plugin from robotframework-agent-plugins.

Source of truth: github.com/robotcodedev/robotframework-agent-plugins
The plugin lives there under ``plugins/robotcode/`` and is mirrored into
``chat-plugins/robotcode/`` in this repo. Run this script to update the
mirror from a local clone of the marketplace repo.

Examples:
    python scripts/sync_chat_plugin.py
    python scripts/sync_chat_plugin.py --check
    python scripts/sync_chat_plugin.py --source ../robotframework-agent-plugins
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEST = REPO_ROOT / "chat-plugins" / "robotcode"
STAMP = REPO_ROOT / "chat-plugins" / ".upstream.json"
DEFAULT_SOURCE = REPO_ROOT.parent / "robotframework-agent-plugins"
PLUGIN_SUBPATH = Path("plugins") / "robotcode"


def die(msg: str) -> None:
    print(f"sync-chat-plugin: {msg}", file=sys.stderr)
    sys.exit(1)


def git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def equal_trees(a: Path, b: Path) -> bool:
    if not b.exists():
        return False
    a_files = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    b_files = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    if a_files != b_files:
        return False
    return all((a / rel).read_bytes() == (b / rel).read_bytes() for rel in a_files)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Path to a local marketplace clone (default: {DEFAULT_SOURCE}).",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the mirror is out of sync; do not touch files.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite even when chat-plugins/robotcode has uncommitted changes.",
    )
    args = ap.parse_args()

    source_root: Path = args.source.resolve()
    source_plugin = source_root / PLUGIN_SUBPATH
    source_manifest = source_root / ".plugin" / "marketplace.json"

    if not source_manifest.is_file():
        die(f"no marketplace.json at {source_manifest} (pass --source <path>)")
    if not source_plugin.is_dir():
        die(f"no plugin at {source_plugin}")

    try:
        sha = git(source_root, "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        sha = "unknown"

    if args.check:
        if equal_trees(source_plugin, DEST):
            print("chat-plugin in sync")
            return 0
        print(
            "chat-plugin out of sync — run `python scripts/sync_chat_plugin.py`",
            file=sys.stderr,
        )
        return 1

    try:
        status = git(REPO_ROOT, "status", "--porcelain", "chat-plugins/robotcode")
    except subprocess.CalledProcessError:
        status = ""
    if status and not args.force:
        die("chat-plugins/robotcode has uncommitted changes (commit/stash or pass --force)")

    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_plugin, DEST)

    stamp = {
        "source": "github.com/robotcodedev/robotframework-agent-plugins",
        "sha": sha,
        "syncedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    STAMP.write_text(json.dumps(stamp, indent=2) + "\n")

    print(f"synced from {source_plugin} (sha {sha[:7]})")
    print(f"  -> {DEST.relative_to(REPO_ROOT)}")
    print(f"  stamp: {STAMP.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
