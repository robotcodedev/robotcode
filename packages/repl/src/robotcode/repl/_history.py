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
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

from robotcode.robot.config.loader import find_project_root
from robotcode.robot.config.utils import get_cache_dir

HISTORY_FILENAME = "repl_history"
MAX_HISTORY = 1000


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
    don't surface that to the user, the REPL just starts empty.
    """
    target = path or history_path()
    readline_module.set_history_length(MAX_HISTORY)
    try:
        readline_module.read_history_file(str(target))
    except (FileNotFoundError, OSError):
        pass


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
