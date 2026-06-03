"""Block-aware indent helpers for the REPL multi-line editing experience.

Pure-Python, deterministic, no Robot-runtime dependency. Used by:

- `ConsoleInterpreter.get_input()` to pre-compute the indent string
  passed via `prefill=` to the next `read_line()` call (so the
  continuation prompt seeds the user's cursor at the right column).
- `_pt.components` smart-Enter / Shift-Enter key bindings to decide
  whether the buffer still has an open block and what indent the
  inserted newline should carry.

Indent width defaults to 4 spaces — the Robot Framework convention
for test-case-body content inside `*** Test Cases ***`. Not
configurable; could be added later via env var or `robot.toml`
setting if there's demand.
"""

import re
from typing import Iterable, List

# Robot's cell separator: 2+ consecutive spaces or a tab.
_CELL_SEP = re.compile(r"  +|\t")

# Block-opener keywords (matched case-insensitively against the first
# cell of the line). When one of these appears, the next line gets
# one additional level of indent.
_OPENERS = frozenset({"FOR", "WHILE", "IF", "TRY", "GROUP"})

# Closer — pops one level of indent.
_CLOSERS = frozenset({"END"})

# Branch markers (`ELSE`, `ELSE IF`, `EXCEPT`, `FINALLY`) are net-zero
# for the depth counter — they live inside an open block but neither
# open nor close one. The counter ignores them by default; no
# enumeration needed.

_DEFAULT_WIDTH = 4


def _first_cell(line: str) -> str:
    """Return the first non-empty cell of a Robot line, upper-cased.

    Leading whitespace is stripped first (Robot's syntax treats it as
    insignificant within a test-case body). Single spaces inside a
    cell are preserved — `_CELL_SEP` only splits on 2+ spaces or a
    tab, so multi-word block markers like ``ELSE IF`` survive intact.
    """
    stripped = line.strip()
    if not stripped:
        return ""
    return _CELL_SEP.split(stripped, maxsplit=1)[0].upper()


def _block_depth(lines: Iterable[str]) -> int:
    """Net block-nesting depth implied by the given sequence of lines."""
    depth = 0
    for line in lines:
        cell = _first_cell(line)
        if cell in _OPENERS:
            depth += 1
        elif cell in _CLOSERS:
            # Clamp to 0 — a stray `END` at depth 0 is a Robot syntax
            # error, but we shouldn't go negative.
            depth = max(0, depth - 1)
    return depth


def compute_indent(lines: List[str], *, width: int = _DEFAULT_WIDTH) -> str:
    """Indent string for the line that comes *after* `lines`.

    Counts block openers minus closers in the prior lines and returns
    ``" " * (depth * width)``. Returns ``""`` for an empty list or a
    balanced buffer.
    """
    return " " * (_block_depth(lines) * width)


def has_open_block(text: str) -> bool:
    """True if `text` (multi-line, separated by ``\\n``) contains more
    block openers than closers — i.e. would not be a complete Robot
    statement if submitted as-is."""
    return _block_depth(text.splitlines()) > 0
