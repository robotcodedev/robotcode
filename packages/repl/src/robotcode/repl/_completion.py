"""Robot-aware completion candidates for the REPL.

This module is backend-agnostic: it understands Robot's syntax (cells
separated by 2+ spaces or tab, `${...}` / `@{...}` / `&{...}` / `%{...}`
variable wrappers, special leading-cell forms like `Import Library`,
`Import Resource`, `Import Variables`) and answers "what should the
user be offered as a completion here?". Both `ReadlineBackend`
(Stage 2) and `PromptToolkitBackend` (Stage 3) consume the same
`tokenize()` and `candidates_for()` API.

We pull live data straight from `EXECUTION_CONTEXTS.current` — the
REPL runs synchronously inside `suite.run()`, so the active namespace
and variable scope are populated by the time the user hits Tab.

Library / Resource / Variables imports each have **their own** Robot
discovery function (`complete_library_import`, `complete_resource_import`,
`complete_variables_import`) — they live in different namespaces and
recognise different file extensions, so we never share their result
sets. The dispatch logic mirrors the Language Server's per-form
completion handlers in
`packages/language_server/.../robotframework/parts/completion.py`.
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from robot.running.context import EXECUTION_CONTEXTS
from robot.utils import normalize

from robotcode.robot.diagnostics.library_doc import (
    complete_library_import,
    complete_resource_import,
    complete_variables_import,
)
from robotcode.robot.utils import RF_VERSION

# Robot Framework 7.0 renamed `TestLibrary.handlers` → `TestLibrary.keywords`
# (and the same on `UserLibrary` / `ResourceFile`). We pick the attribute
# name once at import time so the iteration loops below stay readable.
_LIB_KEYWORDS_ATTR = "keywords" if RF_VERSION >= (7, 0) else "handlers"

# Same story for the keyword doc-string attribute: RF 7+ uses
# `.short_doc` (matches RF's own naming convention), RF 5/6 used
# `.shortdoc`. Used by `candidates_for_rich()` to feed the
# `display_meta` next to each keyword candidate in the popup.
_KW_SHORT_DOC_ATTR = "short_doc" if RF_VERSION >= (7, 0) else "shortdoc"

# Robot's cell separator: 2+ consecutive spaces or a tab.
_CELL_SEP = re.compile(r"  +|\t")

# Number of spaces the prompt-toolkit backend inserts after a
# keyword completion and on Tab in argument context. Robot's minimum
# cell separator is 2 spaces; the 4-space test-body convention only
# applies to file authoring. At a REPL prompt, 2 keeps typing
# compact. A future CLI option could expose this.
CELL_SEPARATOR = "  "


def find_cell_end(text: str, pos: int) -> int:
    """Position of the next cell separator (2+ spaces / tab) at or
    after `pos`, or end-of-line / end-of-text if none exists."""
    line_end = text.find("\n", pos)
    if line_end == -1:
        line_end = len(text)
    m = _CELL_SEP.search(text, pos, line_end)
    return m.start() if m else line_end


# Variable opener anywhere in the current cell: `[$@&%]{<partial>` with an
# unclosed brace. `(.*)` is the partial variable name typed so far.
_VAR_OPEN = re.compile(r"([\$@&%])\{([^{}]*)$")

_VALID_SIGILS = "$@&%"


def _norm(s: Optional[str]) -> str:
    """Robot's case/whitespace/underscore-insensitive folding."""
    return normalize(s, ignore="_") if s else ""


@dataclass(frozen=True)
class CompletionContext:
    """Where the cursor is and what kind of completion fits.

    `kind` is one of "keyword", "variable", "library", "resource",
    "argument". `replace_start` is the buffer offset where the
    *replaceable token* begins — the caller substitutes
    `buffer[replace_start:cursor]` with the chosen candidate. `prefix`
    is the partial token the user has typed (for variable-context, the
    name without sigil/brace).
    """

    kind: str
    prefix: str
    replace_start: int
    sigil: str = ""  # only set for `kind == "variable"`


def tokenize(buffer: str, cursor: int) -> CompletionContext:
    """Inspect the buffer up to `cursor` and classify the typing context."""
    text = buffer[:cursor]

    # Locate the current cell start by walking back past the last cell
    # separator. Default: cursor is in the first cell, cell starts at 0.
    cell_start = 0
    prior_cells: List[str] = []
    matches = list(_CELL_SEP.finditer(text))
    if matches:
        last_sep = matches[-1]
        cell_start = last_sep.end()
        prior_cells = _CELL_SEP.split(text[: last_sep.start()])

    current_cell = text[cell_start:]

    # Variable-completion: unclosed `[$@&%]{...` anywhere in the current cell.
    var_m = _VAR_OPEN.search(current_cell)
    if var_m:
        sigil = var_m.group(1)
        name_partial = var_m.group(2)
        # `replace_start` points at the sigil so the substitution wipes
        # the entire `${partial` and writes `${NAME}` back in.
        replace_start = cell_start + var_m.start()
        return CompletionContext("variable", name_partial, replace_start, sigil=sigil)

    # Cell-level dispatch.
    if not prior_cells:
        return CompletionContext("keyword", current_cell, cell_start)

    first_cell = prior_cells[0].strip()
    folded = first_cell.casefold()
    if folded == "import library":
        return CompletionContext("library", current_cell, cell_start)
    if folded == "import resource":
        return CompletionContext("resource", current_cell, cell_start)
    if folded == "import variables":
        return CompletionContext("variables", current_cell, cell_start)

    return CompletionContext("argument", current_cell, cell_start)


_LIBRARY_KINDS = {"MODULE_INTERNAL", "MODULE", "FILE", "FOLDER"}
_RESOURCE_KINDS = {"RESOURCE", "FILE", "FOLDER"}
_VARIABLES_KINDS = {"MODULE_INTERNAL", "MODULE", "VARIABLES_MODULE", "VARIABLES", "FILE", "FOLDER"}

# Session-lifetime cache of the "full discovery" result for each
# `complete_*_import(None, working_dir=…)` call. That branch walks
# `sys.path` + the project filesystem and returns hundreds of
# CompleteResult objects — expensive enough that re-running it on
# every keystroke (with `complete_while_typing=True` in the
# prompt_toolkit backend) would lag the popup. The cache is keyed
# by `(api-name, working_dir)`; nothing under our feet changes the
# discoverable-modules set during a REPL session, so we never need
# to invalidate.
_FULL_LIST_CACHE: Dict[Tuple[str, str], List[Any]] = {}


def _clear_full_list_cache() -> None:
    """Test-only: drop the discovery cache so a fresh patched `api()` runs again."""
    _FULL_LIST_CACHE.clear()


@dataclass(frozen=True)
class Candidate:
    """A completion candidate plus its display metadata.

    `label` is the full text that gets inserted into the buffer when
    the user picks the candidate — same string `candidates_for()`
    returns. `detail` is the short-form context shown next to the
    label in the completion popup (e.g. the keyword's first-doc-line,
    the import kind, the variable's repr()-ed value).
    """

    label: str
    detail: str = ""


def candidates_for(ctx: CompletionContext, *, working_dir: str = ".") -> List[str]:
    """Return completion strings appropriate for `ctx`.

    Variable references (`kind == "variable"`) come back fully wrapped
    (e.g. ``${TEST_NAME}``) so they're drop-in replacements for the
    partial ``${TEST`` the user is editing. Keyword candidates are
    raw labels. Import-form candidates carry the full user-typed
    prefix back (``robot.libraries.Coll`` → ``robot.libraries.Collections``).

    Thin projection over `candidates_for_rich` — the rich path is the
    single source of truth, this just strips the `detail` field for
    callers that don't render two-column popups.
    """
    return [c.label for c in candidates_for_rich(ctx, working_dir=working_dir)]


def candidates_for_rich(ctx: CompletionContext, *, working_dir: str = ".") -> List[Candidate]:
    """Return completion candidates with their `display_meta` detail:

    - **keyword**: first line of the keyword's docstring (`short_doc`
      on RF 7+, `shortdoc` on RF 5/6) — empty if missing.
    - **variable** (`${…}` / `@{…}` / `&{…}`): `repr(value)[:40]` from
      the live suite scope.
    - **variable** (`%{…}` env var): `repr(os.environ[name])[:40]`.
    - **library / resource / variables import**: `CompleteResult.kind`
      value (e.g. `MODULE`, `MODULE_INTERNAL`, `RESOURCE`, `FILE`).
    """
    if ctx.kind == "keyword":
        return _filter_robot_normalised(_iter_keywords(), ctx.prefix)
    if ctx.kind == "variable":
        # `%{X}` resolves against `os.environ`, not Robot's suite scope.
        items: Iterable[Tuple[str, str]]
        if ctx.sigil == "%":
            items = ((k, _short_repr(v)) for k, v in os.environ.items())
        else:
            items = _iter_variables()
        filtered = _filter_robot_normalised(items, ctx.prefix)
        return [Candidate(label=f"{ctx.sigil}{{{c.label}}}", detail=c.detail) for c in filtered]
    # Library / Resource / Variables map to the matching `Settings`
    # entries — same separator-semantics dispatch as the language
    # server's `complete_LibraryImport` / `…ResourceImport` / `…VariablesImport`:
    # library + variables accept dotted module paths, resource doesn't.
    if ctx.kind == "library":
        return _import_completions(
            ctx.prefix, working_dir, api=complete_library_import, allow_kinds=_LIBRARY_KINDS, support_dotted=True
        )
    if ctx.kind == "resource":
        return _import_completions(
            ctx.prefix, working_dir, api=complete_resource_import, allow_kinds=_RESOURCE_KINDS, support_dotted=False
        )
    if ctx.kind == "variables":
        return _import_completions(
            ctx.prefix, working_dir, api=complete_variables_import, allow_kinds=_VARIABLES_KINDS, support_dotted=True
        )
    return []


def _import_completions(
    prefix: str,
    working_dir: str,
    *,
    api: Callable[..., Optional[List[Any]]],
    allow_kinds: Set[str],
    support_dotted: bool,
) -> List[Candidate]:
    """Three-mode dispatch for library / resource / variables imports.

    Each Robot discovery API behaves as a directory listing — pass a
    head (or ``None`` for the global namespace), get back the entries
    reachable from there. Candidates carry the full reconstructed
    cell (head + matching child).

    Modes picked from the prefix syntax:

    1. Plain identifier / empty prefix: `api(None)`, filter by prefix.
    2. Filesystem path (`/` or `\\`): split at last separator,
       `api(dir_part)`, filter by partial.
    3. Dotted module path (`support_dotted=True` only): split at last
       `.`, `api(base + ".")`. Resource imports skip this because
       Robot treats `common.resource` as a filename, not a path.
    """

    def _fetch(name: Optional[str]) -> List[Any]:
        # Cache the full-discovery (`name=None`) call — it walks
        # `sys.path` + the project filesystem and is the only branch
        # expensive enough to lag live-as-you-type completion.
        # Subdir / dotted-head lookups bypass the cache.
        if name is None:
            key = (api.__name__, working_dir)
            cached = _FULL_LIST_CACHE.get(key)
            if cached is not None:
                return cached
            try:
                results = list(api(None, working_dir=working_dir, base_dir=working_dir) or [])
            except Exception:
                results = []
            _FULL_LIST_CACHE[key] = results
            return results
        try:
            return list(api(name, working_dir=working_dir, base_dir=working_dir) or [])
        except Exception:
            return []

    def _collect(results: List[Any], head: str, partial: str) -> List[Candidate]:
        partial_cf = partial.casefold()
        seen: Dict[str, Candidate] = {}
        for r in results:
            if r.kind.name not in allow_kinds:
                continue
            if partial and not r.label.casefold().startswith(partial_cf):
                continue
            full = head + r.label
            seen.setdefault(full, Candidate(label=full, detail=r.kind.name))
        return sorted(seen.values(), key=lambda c: c.label)

    if not prefix:
        return _collect(_fetch(None), "", "")
    if "/" in prefix or "\\" in prefix:
        sep_idx = max(prefix.rfind("/"), prefix.rfind("\\"))
        dir_part = prefix[: sep_idx + 1]
        return _collect(_fetch(dir_part), dir_part, prefix[sep_idx + 1 :])
    if support_dotted and "." in prefix:
        base, _, partial = prefix.rpartition(".")
        return _collect(_fetch(base + "."), f"{base}.", partial)
    return _collect(_fetch(None), "", prefix)


# ---------------------------------------------------------------------------
# Robot runtime introspection — private helpers, isolated so a future
# RF-API change only touches this section.
# ---------------------------------------------------------------------------


def _iter_keywords() -> Iterator[Tuple[str, str]]:
    """Yield `(name, short_doc)` for every keyword in scope.

    The keyword container moved between Robot versions (see
    `_LIB_KEYWORDS_ATTR`); the doc-attribute name moved too
    (`short_doc` on RF 7+, `shortdoc` on RF 5/6, via
    `_KW_SHORT_DOC_ATTR`). Library-defined keywords win over
    resource-defined ones with the same name (first-seen-wins).
    """
    context = EXECUTION_CONTEXTS.current
    if context is None:
        return
    store = getattr(context.namespace, "_kw_store", None)
    if store is None:
        return
    seen: Set[str] = set()
    sources = (*store.libraries.values(), *store.resources.values())
    for src in sources:
        for kw in getattr(src, _LIB_KEYWORDS_ATTR, ()) or ():
            name = getattr(kw, "name", None)
            if name and name not in seen:
                seen.add(name)
                yield name, getattr(kw, _KW_SHORT_DOC_ATTR, "") or ""


def _iter_variables() -> Iterator[Tuple[str, str]]:
    """Yield `(name, repr(value)[:40])` for every variable in scope.

    Strips Robot's `${…}` decoration from `as_dict()` keys so the
    name matches what the user types inside `${`. The repr is
    truncated so a huge list / dict can't blow out the popup width.
    """
    context = EXECUTION_CONTEXTS.current
    if context is None:
        return
    for decorated, value in context.variables.as_dict().items():
        name = str(decorated)
        if len(name) >= 3 and name[0] in _VALID_SIGILS and name[1] == "{" and name[-1] == "}":
            name = name[2:-1]
        yield name, _short_repr(value)


def _short_repr(value: object, max_len: int = 40) -> str:
    """``repr(value)`` truncated to `max_len` chars with an ellipsis."""
    try:
        r = repr(value)
    except Exception:
        return ""
    if len(r) > max_len:
        return r[: max_len - 1] + "…"
    return r


def _filter_robot_normalised(items: Iterable[Tuple[str, str]], prefix: str) -> List[Candidate]:
    """Robot-normalised prefix filter for `(name, detail)` pairs.

    Dedupes by name (first-seen-wins, matching the iteration order
    of `_iter_keywords` / `_iter_variables`). Sorted by label for
    predictable menu order.
    """
    target = _norm(prefix) if prefix else ""
    seen_names: Set[str] = set()
    result: List[Candidate] = []
    for name, detail in items:
        if target and not _norm(name).startswith(target):
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        result.append(Candidate(label=name, detail=detail))
    result.sort(key=lambda c: c.label)
    return result
