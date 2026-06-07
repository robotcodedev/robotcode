"""Export a recorded REPL session as a runnable ``.robot`` file.

`ConsoleInterpreter._session_lines` accumulates inputs that
round-tripped through Robot's parser; `render_robot_file` builds a
runnable file from them, hoisting ``Import Library/Resource/Variables``
lines into ``*** Settings ***``.
"""

import re
from datetime import datetime
from typing import List, Tuple

_CELL_SEP = re.compile(r"  +|\t")

# `import library` etc. are case-insensitive in Robot — fold for the match.
# The bare `library` / `resource` / `variables` forms are the REPL-only setting
# aliases (see `ConsoleInterpreter._alias_setting_imports`); hoist them too so a
# session typed with Settings-style syntax round-trips into `*** Settings ***`.
_IMPORT_HEADS = {
    "import library": "Library",
    "import resource": "Resource",
    "import variables": "Variables",
    "library": "Library",
    "resource": "Resource",
    "variables": "Variables",
}


def split_imports_and_body(lines: List[str]) -> Tuple[List[str], List[str]]:
    """Hoist single-line ``Import …`` rows into a settings list.

    Returns ``(settings, body)``. Multi-line entries (e.g. ``FOR``
    blocks typed as one input) are never split — they always go into
    the body to preserve structure.
    """
    settings: List[str] = []
    body: List[str] = []
    for entry in lines:
        if "\n" in entry:
            body.append(entry)
            continue
        cells = _CELL_SEP.split(entry.lstrip())
        if not cells:
            body.append(entry)
            continue
        head = cells[0].strip().casefold()
        target = _IMPORT_HEADS.get(head)
        if target is None:
            body.append(entry)
            continue
        rest = cells[1:]
        settings.append("    ".join([target, *rest]))
    return settings, body


def _indent_body_entry(entry: str, indent: str = "    ") -> str:
    out: List[str] = []
    for line in entry.split("\n"):
        out.append(f"{indent}{line}" if line.strip() else line)
    return "\n".join(out)


def render_robot_file(lines: List[str], *, test_name: str = "") -> str:
    """Render a runnable ``.robot`` file from session inputs.

    ``test_name`` defaults to ``REPL Session <ISO-timestamp>``. The
    settings section is omitted when no imports were used.
    """
    if not test_name:
        test_name = f"REPL Session {datetime.now().isoformat(timespec='seconds')}"  # noqa: DTZ005

    settings, body = split_imports_and_body(lines)

    chunks: List[str] = []
    if settings:
        chunks.append("*** Settings ***")
        chunks.extend(settings)
        chunks.append("")

    chunks.append("*** Test Cases ***")
    chunks.append(test_name)
    for entry in body:
        chunks.append(_indent_body_entry(entry))
    chunks.append("")  # file ends with a newline

    return "\n".join(chunks)
