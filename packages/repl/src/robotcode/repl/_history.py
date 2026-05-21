"""Persistent REPL history — file location + readline integration.

The history file lives under the robotcode cache directory: inside a
project (`{project_root}/.robotcode_cache/`) when one is detected, or
in the per-user platform cache otherwise. The `ROBOTCODE_CACHE_DIR`
env var overrides both, matching the analyzer's existing convention.
Readline and prompt_toolkit both consume `history_path()` so switching
between backends doesn't lose entries.
"""

import atexit
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

from robotcode.robot.config.loader import find_project_root
from robotcode.robot.config.utils import get_cache_dir

HISTORY_FILENAME = "repl_history"
DEFAULT_MAX_HISTORY = 1000
HISTORY_SIZE_ENV_VAR = "ROBOTCODE_REPL_HISTORY_SIZE"


def max_history_size() -> int:
    """Return the configured history-buffer size.

    Reads `ROBOTCODE_REPL_HISTORY_SIZE` if set to a positive integer;
    otherwise falls back to `DEFAULT_MAX_HISTORY` (1000). Negative or
    non-numeric values are ignored — we never raise on bad input from
    an env var, the REPL just uses the default.
    """
    raw = os.environ.get(HISTORY_SIZE_ENV_VAR)
    if not raw:
        return DEFAULT_MAX_HISTORY
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_HISTORY
    return value if value > 0 else DEFAULT_MAX_HISTORY


def history_path() -> Path:
    """Return the absolute path to the REPL history file.

    Project-aware: drops into `.robotcode_cache/` if invoked inside a
    Robot project, otherwise into the per-user platform cache.
    """
    project_root, _ = find_project_root()
    cache_dir = get_cache_dir(project_root)
    return cache_dir / HISTORY_FILENAME


def load_into_readline(readline_module: ModuleType, path: Optional[Path] = None) -> None:
    """Load the history file into `readline`'s in-memory ring buffer.

    A missing or unreadable file is treated as "no prior history" — we
    don't surface that to the user, the REPL just starts empty. After
    loading, in-memory duplicates are folded the same way as on
    insertion: a backlog from a pre-dedup version of the code is
    cleaned up automatically on next start.
    """
    target = path or history_path()
    readline_module.set_history_length(max_history_size())
    try:
        readline_module.read_history_file(str(target))
    except (FileNotFoundError, OSError):
        pass
    else:
        _dedup_history(readline_module)


def remove_history_items(readline_module: ModuleType, indices: list[int]) -> None:
    """Remove history entries at the given 0-based indices.

    Prefers `readline.remove_history_item` when the module exposes it
    (CPython's GNU readline, gnureadline, libedit). Falls back to a
    `clear_history` + re-`add_history` rebuild for shims that don't
    implement it — notably ``pyreadline3`` on Windows, where the
    missing attr would otherwise crash REPL startup the first time
    legacy duplicate entries are dedup'd.
    """
    if not indices:
        return
    if hasattr(readline_module, "remove_history_item"):
        # Sort high → low so each removal keeps the lower indices stable.
        for idx in sorted(set(indices), reverse=True):
            readline_module.remove_history_item(idx)
        return
    drop = set(indices)
    length = readline_module.get_current_history_length()
    survivors = [readline_module.get_history_item(i) for i in range(1, length + 1) if (i - 1) not in drop]
    readline_module.clear_history()
    for item in survivors:
        if item is not None:
            readline_module.add_history(item)


def dedup_last_entry(readline_module: ModuleType) -> None:
    """Remove older duplicates of the most recently added history entry.

    Fish-style behaviour: when the user types a line that's already in
    the history, the older occurrences disappear so the entry only
    shows up once when arrow-up-ing. Whitespace-only or empty entries
    are left untouched.
    """
    length = readline_module.get_current_history_length()
    if length <= 1:
        return
    latest = readline_module.get_history_item(length)
    if not latest or not latest.strip():
        return
    to_drop = [i - 1 for i in range(length - 1, 0, -1) if readline_module.get_history_item(i) == latest]
    remove_history_items(readline_module, to_drop)


def _dedup_history(readline_module: ModuleType) -> None:
    """Remove all duplicate entries from readline's history buffer.

    Keeps the latest occurrence of each unique line, drops older copies.
    Used by `load_into_readline` to clean up files saved by pre-dedup
    versions of the code.
    """
    length = readline_module.get_current_history_length()
    seen: set[str] = set()
    # Iterate newest → oldest, marking each line the first time we see
    # it. Anything we encounter a second time is a stale duplicate.
    to_drop: list[int] = []
    for i in range(length, 0, -1):
        item = readline_module.get_history_item(i)
        if item in seen:
            to_drop.append(i - 1)  # 0-based
        else:
            seen.add(item)
    remove_history_items(readline_module, to_drop)


def truncate_history_file(path: Optional[Path] = None) -> None:
    """Wipe the on-disk history file (zero-byte truncate).

    Used by `.history clear`. Missing file is treated as already-empty.
    """
    target = path or history_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("", encoding="utf-8")
    except OSError:
        pass


def delete_history_line_in_file(idx: int, path: Optional[Path] = None) -> bool:
    """Remove the 1-based line at ``idx`` from the history file.

    Returns ``True`` when a line was actually dropped, ``False`` when
    the file is missing or the index falls outside its bounds.
    """
    target = path or history_path()
    try:
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    except (FileNotFoundError, OSError):
        return False
    if not (1 <= idx <= len(lines)):
        return False
    del lines[idx - 1]
    try:
        target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    except OSError:
        return False
    return True


def attach_save_on_exit(readline_module: ModuleType, path: Optional[Path] = None) -> None:
    """Register an `atexit` hook that writes readline's history on shutdown.

    Skipped silently when stdin is not a TTY (piped input, CI runs) —
    those sessions would otherwise pollute the history with one-shot
    automation lines.
    """
    if not sys.stdin.isatty():
        return

    target = path or history_path()

    def _save() -> None:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            readline_module.write_history_file(str(target))
        except OSError:
            # Disk full, permission denied, … — silently drop. Losing
            # history is preferable to crashing the REPL on exit.
            pass

    atexit.register(_save)
