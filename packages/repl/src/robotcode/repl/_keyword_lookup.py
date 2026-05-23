"""Robot library / keyword runtime lookup helpers.

Backend-agnostic: both `ConsoleInterpreter` (plain) and
`PromptToolkitConsoleInterpreter` use these to resolve `.kw <name>`
and `.doc <library>` dot-commands against the currently-imported
`_kw_store`. The richer completion machinery (tokenize / candidates
/ CompletionContext / Candidate) is prompt_toolkit-only and lives
in `_pt.completion`.

Data is pulled straight from `EXECUTION_CONTEXTS.current`, which is
populated by the time the user hits Enter because the REPL runs
synchronously inside `suite.run()`.
"""

from typing import Any, Optional

from robot.running.context import EXECUTION_CONTEXTS
from robot.utils import normalize

from robotcode.robot.utils import RF_VERSION

# Robot Framework 7.0 renamed `TestLibrary.handlers` → `TestLibrary.keywords`
# (and the same on `UserLibrary` / `ResourceFile`). Picked once at
# import time so the iteration loops stay readable.
_LIB_KEYWORDS_ATTR = "keywords" if RF_VERSION >= (7, 0) else "handlers"


def _norm(s: Optional[str]) -> str:
    """Robot's case/whitespace/underscore-insensitive folding."""
    return normalize(s, ignore="_") if s else ""


def lookup_keyword_doc(name: str) -> Optional[Any]:
    """Resolve ``name`` to a loaded keyword object, or ``None``.

    Matches Robot's case/whitespace/underscore-insensitive lookup
    (``Set Variable`` == ``set_variable``); library-defined keywords
    win over resource-defined ones on name collisions. The returned
    object is whatever ``_kw_store`` holds — typically a Robot runtime
    keyword with ``.name``, ``.args`` (``ArgumentSpec``), ``.doc``,
    ``.tags``, ``.source``. Callers should access fields defensively.
    """
    context = EXECUTION_CONTEXTS.current
    if context is None:
        return None
    store = getattr(context.namespace, "_kw_store", None)
    if store is None:
        return None
    target = _norm(name)
    if not target:
        return None
    for src in (*store.libraries.values(), *store.resources.values()):
        for kw in getattr(src, _LIB_KEYWORDS_ATTR, ()) or ():
            kw_name = getattr(kw, "name", None)
            if kw_name and _norm(kw_name) == target:
                return kw
    return None


def lookup_library_doc(name: str) -> Optional[Any]:
    """Resolve ``name`` to a loaded library or resource, or ``None``.

    Case-insensitive lookup against `_kw_store`. The returned object
    exposes ``.name``, ``.keywords`` / ``.handlers``, ``.doc``,
    ``.doc_format``, ``.source``. For libraries that aren't currently
    imported, callers can fall back to
    `robotcode.robot.diagnostics.library_doc.get_library_doc`.
    """
    context = EXECUTION_CONTEXTS.current
    if context is None:
        return None
    store = getattr(context.namespace, "_kw_store", None)
    if store is None:
        return None
    target = name.casefold()
    if not target:
        return None
    for src in (*store.libraries.values(), *store.resources.values()):
        src_name = getattr(src, "name", None)
        if src_name and str(src_name).casefold() == target:
            return src
    return None
