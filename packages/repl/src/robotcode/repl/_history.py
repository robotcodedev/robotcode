"""Persistent REPL history — file location + readline integration.

The history file lives under the robotcode cache directory: inside a
project (`{project_root}/.robotcode_cache/`) when one is detected, or
in the per-user platform cache otherwise. The `ROBOTCODE_CACHE_DIR`
env var overrides both, matching the analyzer's existing convention.

Stage 1 wires this into the readline backend. Stage 3 reuses
`history_path()` for prompt_toolkit's `FileHistory`, so switching
backends never loses history.
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
    # Walk from second-newest down to oldest, removing matches. Iterating
    # backwards keeps the indices we still need to inspect stable.
    for i in range(length - 1, 0, -1):
        if readline_module.get_history_item(i) == latest:
            readline_module.remove_history_item(i - 1)  # 0-based index


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
            to_drop.append(i - 1)  # 0-based for remove
        else:
            seen.add(item)
    # Remove from highest index down so earlier indices stay valid.
    for idx in to_drop:
        readline_module.remove_history_item(idx)


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
