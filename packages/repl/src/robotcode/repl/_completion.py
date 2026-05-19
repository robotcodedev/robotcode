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

# Robot's cell separator: 2+ consecutive spaces or a tab.
_CELL_SEP = re.compile(r"  +|\t")
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


def candidates_for(ctx: CompletionContext, *, working_dir: str = ".") -> List[str]:
    """Return completion strings appropriate for `ctx`.

    Variable references (`kind == "variable"`) come back fully wrapped
    (e.g. ``${TEST_NAME}``) so they're drop-in replacements for the
    partial ``${TEST`` the user is editing. Keyword candidates are
    raw labels.

    Import-form candidates (``library`` / ``resource`` / ``variables``)
    carry their *full* user-typed prefix back: ``robot.libraries.Coll``
    returns ``robot.libraries.Collections``; ``./libs/My`` returns
    ``./libs/MyLib.py``. The user's whole cell is replaced verbatim
    regardless of which Robot-supported addressing scheme they're
    typing.
    """
    if ctx.kind == "keyword":
        return _filter_robot_normalised(_iter_keywords(), ctx.prefix)
    if ctx.kind == "variable":
        # `%{X}` is a *Robot environment variable* — resolved against
        # `os.environ` at runtime, NOT against the suite's variable
        # scope. The other sigils (`$`/`@`/`&`) share Robot's namespace.
        source: Iterable[str] = os.environ.keys() if ctx.sigil == "%" else _iter_variables()
        names = _filter_robot_normalised(source, ctx.prefix)
        return [f"{ctx.sigil}{{{n}}}" for n in names]

    # Library / Resource / Variables each map to the matching `Settings`
    # entry in a `.robot` file: `Library`, `Resource`, `Variables`. The
    # language server's `complete_LibraryImport` / `complete_ResourceImport`
    # / `complete_VariablesImport` decide on separator semantics the same
    # way (see packages/language_server/.../parts/completion.py):
    #
    # - Library  → dotted module paths supported (no `/` in input).
    # - Resource → file-system paths only; `.` is treated as part of the
    #              filename (`common.resource`), not a module separator.
    # - Variables → dotted module paths supported (parallel to Library).
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
) -> List[str]:
    """Generic three-mode dispatch for library / resource / variables imports.

    Each Robot discovery API behaves as a *directory listing* — pass
    it a head (or `None` for "the global namespace"), get back the
    entries reachable from that head. The candidates we return are
    the **full reconstructed cell**: head plus matching child, ready
    to drop into the line.

    Modes, picked from the prefix syntax:

    1. **Plain identifier or empty prefix** (no `.` `/` `\\`): call
       ``api(None)``, filter by prefix. Matches the language server's
       behaviour — whatever sys.path / project / built-ins Robot
       discovers, we surface.
    2. **Filesystem path** (contains `/` or `\\`): split at the last
       separator, ``api(dir_part)``, filter by partial, prepend
       ``dir_part`` back.
    3. **Dotted module path** (contains `.`, only with
       ``support_dotted=True``): split at the last `.`, ask Robot for
       submodules of the head, stitch the head back. Resource imports
       skip this mode because Robot itself doesn't translate dots for
       them — `common.resource` is a filename, not `common/resource`.
    """

    def _fetch(name: Optional[str]) -> List[Any]:
        # The `name=None` branch (full discovery) is the expensive one —
        # serve it from the session cache so live-as-you-type completion
        # in the prompt_toolkit backend doesn't re-walk `sys.path` on
        # every keystroke. Subdir / dotted-head lookups are cheap and
        # bypass the cache (their result depends on the partial input).
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

    # Empty prefix — full discovery, no filter.
    if not prefix:
        results = _fetch(None)
        return sorted({r.label for r in results if r.kind.name in allow_kinds})

    # Filesystem path (`/` or `\`) takes precedence — `./libs/foo.bar`
    # is a path, not a dotted module.
    if "/" in prefix or "\\" in prefix:
        sep_idx = max(prefix.rfind("/"), prefix.rfind("\\"))
        dir_part = prefix[: sep_idx + 1]
        partial = prefix[sep_idx + 1 :]
        results = _fetch(dir_part)
        partial_cf = partial.casefold()
        return sorted(
            {
                dir_part + r.label
                for r in results
                if r.kind.name in allow_kinds and r.label.casefold().startswith(partial_cf)
            }
        )

    # Dotted module path — library + variables only.
    if support_dotted and "." in prefix:
        base, _, partial = prefix.rpartition(".")
        results = _fetch(base + ".")
        partial_cf = partial.casefold()
        return sorted(
            {
                f"{base}.{r.label}"
                for r in results
                if r.kind.name in allow_kinds and r.label.casefold().startswith(partial_cf)
            }
        )

    # Plain identifier — full discovery, filter by prefix locally.
    results = _fetch(None)
    prefix_cf = prefix.casefold()
    return sorted({r.label for r in results if r.kind.name in allow_kinds and r.label.casefold().startswith(prefix_cf)})


# ---------------------------------------------------------------------------
# Robot runtime introspection — private helpers, isolated so a future
# RF-API change only touches this section.
# ---------------------------------------------------------------------------


def _iter_keywords() -> Iterator[str]:
    """Yield every keyword name reachable from the live execution context.

    The keyword container moved between Robot versions:

    - RF 7.0+: ``library.keywords`` → ``list[LibraryKeyword]`` (each
      with ``.name``).
    - RF 5/6: ``library.handlers`` → ``KeywordStore`` of ``Handler``
      instances (each also with ``.name``).

    ``_LIB_KEYWORDS_ATTR`` (selected once at module import) tells us
    which attribute to read; resources expose the same name.
    """
    context = EXECUTION_CONTEXTS.current
    if context is None:
        return
    store = getattr(context.namespace, "_kw_store", None)
    if store is None:
        return
    seen: Set[str] = set()
    for lib in store.libraries.values():
        for kw in getattr(lib, _LIB_KEYWORDS_ATTR, ()) or ():
            name = getattr(kw, "name", None)
            if name and name not in seen:
                seen.add(name)
                yield name
    for resource in store.resources.values():
        for kw in getattr(resource, _LIB_KEYWORDS_ATTR, ()) or ():
            name = getattr(kw, "name", None)
            if name and name not in seen:
                seen.add(name)
                yield name


def _iter_variables() -> Iterator[str]:
    """Yield variable names (without the `${}` wrapping) from current scope."""
    context = EXECUTION_CONTEXTS.current
    if context is None:
        return
    for decorated in context.variables.as_dict().keys():
        name = str(decorated)
        # `as_dict(decoration=True)` returns names like `${VAR}` — strip
        # the wrapping so the partial-typed name matches what's inside `${`.
        if len(name) >= 3 and name[0] in _VALID_SIGILS and name[1] == "{" and name[-1] == "}":
            yield name[2:-1]
        else:
            yield name


# ---------------------------------------------------------------------------
# Filtering — Robot's case/whitespace/underscore-insensitive prefix match.
# ---------------------------------------------------------------------------


def _filter_robot_normalised(labels: Iterable[str], prefix: str) -> List[str]:
    """Return unique labels whose normalised form starts with `prefix` normalised.

    Sorted alphabetically (canonical case) — completion menus look more
    predictable that way than insertion-order.
    """
    if not prefix:
        return sorted(set(labels))
    target = _norm(prefix)
    return sorted({label for label in labels if _norm(label).startswith(target)})
