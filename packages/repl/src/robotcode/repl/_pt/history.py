"""Persistent REPL history — file location + size cap.

The history file lives under the robotcode cache directory: inside a
project (`{project_root}/.robotcode_cache/`) when one is detected, or
in the per-user platform cache otherwise. `ROBOTCODE_CACHE_DIR`
overrides both, matching the analyzer's existing convention.

Only `PromptToolkitConsoleInterpreter` owns the file at runtime
(through `_ReplFileHistory` in `_pt.components`); this module just
exposes the path and the configured cap.
"""

import os
from pathlib import Path

from robotcode.robot.config.loader import find_project_root
from robotcode.robot.config.utils import get_cache_dir

HISTORY_FILENAME = "repl_history"
DEFAULT_MAX_HISTORY = 10000
HISTORY_SIZE_ENV_VAR = "ROBOTCODE_REPL_HISTORY_SIZE"


def history_path() -> Path:
    """Absolute path to the REPL history file.

    Project-aware: `.robotcode_cache/` when invoked inside a Robot project,
    otherwise the per-user platform cache.
    """
    project_root, _ = find_project_root()
    cache_dir = get_cache_dir(project_root)
    return cache_dir / HISTORY_FILENAME


def max_history_size() -> int:
    """Configured history-buffer cap, from `ROBOTCODE_REPL_HISTORY_SIZE`.

    Negative or non-numeric values fall back to `DEFAULT_MAX_HISTORY` (10000) —
    bad input from an env var should never raise.
    """
    raw = os.environ.get(HISTORY_SIZE_ENV_VAR)
    if not raw:
        return DEFAULT_MAX_HISTORY
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_HISTORY
    return value if value > 0 else DEFAULT_MAX_HISTORY
