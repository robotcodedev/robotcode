"""Robot-aware completion candidates for the REPL — the pure core logic.

Despite living under `_pt/`, this module has **no** prompt_toolkit dependency:
it's the shared completion service driven by the `_RobotCompleter` renderer (in
`_pt.components`), the bottom-toolbar signature hint, and the debugger prompt,
via `tokenize()` + `candidates_for()` / `complete_commands()`. It is
context/scope-aware — `_iter_keywords`/`_iter_variables` and `candidates_for*`
take an optional `context`/`variables` (a paused frame's scope), defaulting to
`EXECUTION_CONTEXTS.current` (populated by the time the user hits Tab, because
the REPL runs synchronously inside `suite.run()`).

Library / Resource / Variables imports each have their own discovery
function (`complete_library_import`, `complete_resource_import`,
`complete_variables_import`) — they live in different namespaces and
recognise different file extensions, so we never share their results.
The dispatch logic mirrors the Language Server's per-form completion
handlers in `packages/language_server/.../parts/completion.py`.

Robot-runtime lookup helpers used by both interpreters
(`lookup_keyword_doc`, `lookup_library`, `lookup_resource`) live in
`robotcode.repl._keyword_lookup` — those don't depend on
prompt_toolkit and shouldn't import this module.
"""

import inspect
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, List, Literal, Optional, Set, Tuple

from robot.running.context import EXECUTION_CONTEXTS
from robot.variables.search import is_assign as _rf_is_assign

from robotcode.robot.diagnostics.library_doc import (
    complete_library_import,
    complete_resource_import,
    complete_variables_import,
)
from robotcode.robot.utils import RF_VERSION

from .._keyword_lookup import _LIB_KEYWORDS_ATTR, _norm, lookup_keyword_doc

# Same story as `_LIB_KEYWORDS_ATTR`: RF 7+ uses `.short_doc`
# (matches RF's own naming convention), RF 5/6 used `.shortdoc`.
# Used by `candidates_for_rich()` to feed the `display_meta` next
# to each keyword candidate in the popup.
_KW_SHORT_DOC_ATTR = "short_doc" if RF_VERSION >= (7, 0) else "shortdoc"

# REPL-only setting-import aliases offered alongside keyword completions at the
# `>>>` prompt (see `ConsoleInterpreter._alias_setting_imports`). Offered only
# there — not at the `(rdb)` prompt, where the aliases don't apply.
_SETTING_IMPORT_ALIAS_COMPLETIONS: Tuple[Tuple[str, str], ...] = (
    ("Library", "alias for Import Library"),
    ("Resource", "alias for Import Resource"),
    ("Variables", "alias for Import Variables"),
)

# Robot's cell separator: 2+ consecutive spaces or a tab.
_CELL_SEP = re.compile(r"  +|\t")

# Spaces inserted after a keyword completion and on Tab in argument
# context. Robot's minimum cell separator is 2 spaces; the 4-space
# test-body convention only applies to file authoring. At a REPL
# prompt, 2 keeps typing compact.
CELL_SEPARATOR = "  "


def find_cell_end(text: str, pos: int) -> int:
    """Position of the next cell separator (2+ spaces / tab) at or
    after `pos`, or end-of-line / end-of-text if none exists."""
    line_end = text.find("\n", pos)
    if line_end == -1:
        line_end = len(text)
    m = _CELL_SEP.search(text, pos, line_end)
    return m.start() if m else line_end


def current_named_arg_in_cell(buffer: str, cursor: int) -> Optional[str]:
    """Return the ``name`` part of a ``name=…`` cell at the cursor, or ``None``.

    Doesn't check whether ``name`` is actually declared on any
    keyword — callers must verify against the spec separately.
    """
    line_start = buffer.rfind("\n", 0, cursor) + 1
    line_text = buffer[line_start:cursor]
    cells = _CELL_SEP.split(line_text)
    while cells and not cells[0].strip():
        cells.pop(0)
    if len(cells) < 2:
        return None
    m = _NAMED_ARG.match(cells[-1])
    return m.group(1) if m else None


def spec_arg_position(spec: Any, name: str) -> Optional[int]:
    """Position of ``name`` in the keyword's flat argument list.

    Order matches `_spec_arg_items` (positional_only → positional_or_named
    → var_positional → named_only → var_named). When the spec has a
    ``**kwargs`` catch-all, an unknown ``name`` resolves to that slot;
    otherwise it returns ``None``.
    """
    if spec is None:
        return None
    idx = 0
    for declared in getattr(spec, "positional_only", ()) or ():
        if declared == name:
            return idx
        idx += 1
    for declared in getattr(spec, "positional_or_named", ()) or ():
        if declared == name:
            return idx
        idx += 1
    var_positional = getattr(spec, "var_positional", None)
    if var_positional:
        if var_positional == name:
            return idx
        idx += 1
    for declared in getattr(spec, "named_only", ()) or ():
        if declared == name:
            return idx
        idx += 1
    if getattr(spec, "var_named", None):
        return idx
    return None


def current_keyword_and_arg_index(buffer: str, cursor: int) -> Optional[Tuple[str, int]]:
    """``(keyword_name, positional_arg_index)`` for the cursor, or ``None``.

    Returns ``None`` when the cursor sits in cell 0 (still typing the
    keyword name). Indices are scoped to the current logical line, so
    continuation lines inside a ``FOR``/``IF`` body report cells
    relative to that line.
    """
    line_start = buffer.rfind("\n", 0, cursor) + 1
    line_text = buffer[line_start:cursor]
    cells = _CELL_SEP.split(line_text)
    # Skip block-body indentation and return-value assignment targets so the
    # keyword (not a `${x}=` assignment) anchors the argument index.
    cells = cells[_assignment_prefix_len(cells) :]
    if len(cells) < 2:
        return None
    keyword = cells[0].strip()
    if not keyword:
        return None
    return keyword, len(cells) - 2


# Unclosed variable opener: `[$@&%]{<partial>`.
_VAR_OPEN = re.compile(r"([\$@&%])\{([^{}]*)$")

# `name=value` at the start of an argument cell. Identifier is the safe
# alphanum + underscore subset; libraries that use hyphens in named args
# degrade gracefully to plain argument-cell completion.
_NAMED_ARG = re.compile(r"^([A-Za-z_]\w*)=(.*)$")

_VALID_SIGILS = "$@&%"

# Robot Framework's own variable parser recognises every assignment-target form
# — scalar/list/dict, item subscripts (`${x}[0]`, RF 6.1+), and type hints
# (`${x: int}`, RF 7.3+). The `allow_*` keywords were added over time, so pass
# only the ones the installed RF (5.0+) actually accepts (resolved once here).
_IS_ASSIGN_KWARGS = {
    name: True for name in ("allow_nested", "allow_items") if name in inspect.signature(_rf_is_assign).parameters
}


def _is_assign_target(cell: str) -> bool:
    """Whether `cell` is a return-value assignment target — `${x}` / `@{x}` /
    `&{x}`, optionally with an item subscript, a type hint, and/or a trailing
    `=` — using Robot Framework's own parser so we match real syntax exactly."""
    cell = cell.strip()
    if cell.endswith("="):  # the assignment sign (RF allows it on the last target)
        cell = cell[:-1].rstrip()
    return bool(_rf_is_assign(cell, **_IS_ASSIGN_KWARGS))


def _assignment_prefix_len(cells: List[str]) -> int:
    """How many leading cells to skip to reach the keyword cell.

    Skips block-body indentation (empty cells) and any return-value assignment
    targets, so `${r}=    Some Keyword` anchors on `Some Keyword`, not `${r}=`.
    """
    i = 0
    while i < len(cells) and not cells[i].strip():
        i += 1
    while i < len(cells) and _is_assign_target(cells[i]):
        i += 1
    return i


@dataclass(frozen=True)
class CompletionContext:
    """Where the cursor is and what kind of completion fits.

    ``kind`` is one of ``"keyword"``, ``"variable"``, ``"library"``,
    ``"resource"``, ``"variables"``, ``"argument"``, ``"named_arg_value"``.
    Callers substitute ``buffer[replace_start:cursor]`` with the chosen
    candidate. ``sigil`` is only set for ``"variable"``;
    ``keyword_name`` and ``arg_name`` only for ``"named_arg_value"``.
    """

    kind: str
    prefix: str
    replace_start: int
    sigil: str = ""
    keyword_name: str = ""
    arg_name: str = ""


def tokenize(buffer: str, cursor: int, *, setting_import_aliases: bool = False) -> CompletionContext:
    """Classify the typing context at `cursor`.

    With `setting_import_aliases` (the `>>>` prompt), a bare `Library` /
    `Resource` / `Variables` first cell routes its argument to import completion,
    exactly like the `Import …` keyword it aliases.
    """
    text = buffer[:cursor]

    cell_start = 0
    prior_cells: List[str] = []
    matches = list(_CELL_SEP.finditer(text))
    if matches:
        last_sep = matches[-1]
        cell_start = last_sep.end()
        prior_cells = _CELL_SEP.split(text[: last_sep.start()])

    current_cell = text[cell_start:]

    var_m = _VAR_OPEN.search(current_cell)
    if var_m:
        sigil = var_m.group(1)
        name_partial = var_m.group(2)
        # Point `replace_start` at the sigil so the whole `${partial`
        # gets replaced when a candidate is picked.
        replace_start = cell_start + var_m.start()
        return CompletionContext("variable", name_partial, replace_start, sigil=sigil)

    if not prior_cells:
        return CompletionContext("keyword", current_cell, cell_start)

    # Skip block-body indentation and any return-value assignment targets so the
    # keyword cell still gets keyword completion and what follows is classified
    # against the real keyword. (General Robot syntax — not gated by the flag.)
    keyword_cell = _assignment_prefix_len(prior_cells)
    if keyword_cell == len(prior_cells):
        # nothing but indentation and assignment targets so far → keyword cell
        return CompletionContext("keyword", current_cell, cell_start)

    first_cell = prior_cells[keyword_cell].strip()
    folded = first_cell.casefold()
    if folded == "import library" or (setting_import_aliases and folded == "library"):
        return CompletionContext("library", current_cell, cell_start)
    if folded == "import resource" or (setting_import_aliases and folded == "resource"):
        return CompletionContext("resource", current_cell, cell_start)
    if folded == "import variables" or (setting_import_aliases and folded == "variables"):
        return CompletionContext("variables", current_cell, cell_start)

    # `name=value` is a named arg only when `name` is actually declared
    # on the keyword. Robot itself binds `Log    foo=bar` (where `foo`
    # isn't a `Log` argument) as a positional `message="foo=bar"` —
    # mirroring that here keeps Tab's cell-separator behaviour for the
    # literal case instead of opening an empty completion popup.
    named_m = _NAMED_ARG.match(current_cell)
    if named_m and first_cell:
        arg_name = named_m.group(1)
        kw = lookup_keyword_doc(first_cell)
        if kw is not None and _spec_accepts_named_arg(getattr(kw, "args", None), arg_name):
            partial = named_m.group(2)
            value_start = cell_start + named_m.start(2)
            return CompletionContext(
                kind="named_arg_value",
                prefix=partial,
                replace_start=value_start,
                keyword_name=first_cell,
                arg_name=arg_name,
            )

    return CompletionContext("argument", current_cell, cell_start)


_LIBRARY_KINDS = {"MODULE_INTERNAL", "MODULE", "FILE", "FOLDER"}
_RESOURCE_KINDS = {"RESOURCE", "FILE", "FOLDER"}
_VARIABLES_KINDS = {"MODULE_INTERNAL", "MODULE", "VARIABLES_MODULE", "VARIABLES", "FILE", "FOLDER"}

# Session-lifetime cache of the "full discovery" result for each
# `complete_*_import(None, working_dir=…)` call. That branch walks
# `sys.path` + the project filesystem and returns hundreds of
# CompleteResult objects — expensive enough that re-running it on
# every keystroke (`complete_while_typing=True`) would lag the
# popup. The cache is keyed by `(api-name, working_dir)`; nothing
# under our feet changes the discoverable-modules set during a
# REPL session, so we never need to invalidate.
_FULL_LIST_CACHE: Dict[Tuple[str, str], List[Any]] = {}


def _clear_full_list_cache() -> None:
    """Test-only: drop the discovery cache so a fresh patched `api()` runs again."""
    _FULL_LIST_CACHE.clear()


@dataclass(frozen=True)
class Candidate:
    """A completion candidate plus its `display_meta`-side context.

    ``label`` is the text that goes into the buffer; ``detail`` is the
    short context (first-doc-line, import kind, variable repr) shown
    beside it in the popup.
    """

    label: str
    detail: str = ""


# A bare leading dot-command token (`.`, `.co`, …) — no cell separator yet.
_DOT_COMMAND_RE = re.compile(r"^\.(\w*)$")


def command_prefix(text: str) -> Optional[str]:
    """If `text` (the line before the cursor) is a bare dot-command token like
    ``.co``, return the word after the dot (``"co"``); otherwise ``None``.

    Lets a prompt renderer switch into dot-command completion before falling
    through to Robot keyword/variable completion.
    """
    if "\n" in text:
        return None
    m = _DOT_COMMAND_RE.match(text.lstrip())
    return m.group(1) if m else None


def complete_commands(prefix: str, names: Iterable[str]) -> List[Candidate]:
    """Completion candidates for dot-commands (`.continue`, `.help`, …).

    `prefix` is the word *after* the dot (no dot); each candidate's label is the
    full ``.name``. Shared by the REPL and debugger prompt renderers — the
    available command names differ per prompt and are passed in by the caller.
    """
    target = prefix.casefold()
    return [Candidate(label="." + name) for name in sorted(set(names)) if name.casefold().startswith(target)]


def candidates_for(
    ctx: CompletionContext, *, context: Any = None, variables: Any = None, working_dir: str = "."
) -> List[str]:
    """Completion strings (labels only) for ``ctx``.

    Variables come back fully wrapped (``${TEST_NAME}``); keywords are
    raw labels; import-form candidates carry their full reconstructed
    path. Thin projection over `candidates_for_rich`.
    """
    return [c.label for c in candidates_for_rich(ctx, context=context, variables=variables, working_dir=working_dir)]


def candidates_for_rich(
    ctx: CompletionContext,
    *,
    context: Any = None,
    variables: Any = None,
    working_dir: str = ".",
    include_setting_aliases: bool = False,
) -> List[Candidate]:
    """Completion candidates with their `display_meta` detail.

    Per `ctx.kind` the detail carries:

    - ``keyword`` — first line of the keyword's docstring.
    - ``variable`` (``${…}`` / ``@{…}`` / ``&{…}``) — truncated
      ``repr(value)`` from the live suite scope.
    - ``variable`` (``%{…}``) — truncated ``repr(os.environ[name])``.
    - ``library`` / ``resource`` / ``variables`` — ``CompleteResult.kind``
      (``MODULE``, ``RESOURCE``, ``FILE``, …).
    - ``named_arg_value`` — empty (Literal values have no extra context).
    """
    if ctx.kind == "keyword":
        keywords: Iterable[Tuple[str, str]] = _iter_keywords(context)
        if include_setting_aliases:
            keywords = [*keywords, *_SETTING_IMPORT_ALIAS_COMPLETIONS]
        return _filter_robot_normalised(keywords, ctx.prefix)
    if ctx.kind == "variable":
        # `%{X}` resolves against `os.environ`, not Robot's suite scope.
        items: Iterable[Tuple[str, str]]
        if ctx.sigil == "%":
            items = ((k, _short_repr(v)) for k, v in os.environ.items())
        else:
            items = _iter_variables(variables, context)
        filtered = _filter_robot_normalised(items, ctx.prefix)
        return [Candidate(label=f"{ctx.sigil}{{{c.label}}}", detail=c.detail) for c in filtered]
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
    if ctx.kind == "named_arg_value":
        return _named_arg_value_candidates(ctx)
    return []


def _named_arg_value_candidates(ctx: CompletionContext) -> List[Candidate]:
    kw = lookup_keyword_doc(ctx.keyword_name)
    if kw is None:
        return []
    literals = _literal_values_for_named_arg(getattr(kw, "args", None), ctx.arg_name)
    if not literals:
        return []
    target = ctx.prefix.casefold()
    return [Candidate(label=str(v), detail="") for v in literals if str(v).casefold().startswith(target)]


def _spec_accepts_named_arg(spec: Any, name: str) -> bool:
    """True when ``name`` could be passed as a named argument.

    Matches Robot's binding rules: ``positional_or_named`` /
    ``named_only`` accept ``name``, and a ``**kwargs`` catch-all
    accepts anything.
    """
    if spec is None:
        return False
    if name in (getattr(spec, "positional_or_named", ()) or ()):
        return True
    if name in (getattr(spec, "named_only", ()) or ()):
        return True
    if getattr(spec, "var_named", None):
        return True
    return False


def _literal_values_for_named_arg(spec: Any, name: str) -> List[str]:
    """``Literal[…]`` values declared on argument ``name``, or ``[]``.

    RF 7+ exposes ``Literal`` via ``ArgumentSpec.types[name]`` as a
    ``TypeInfo``; older Robot versions store bare classes there, so
    the walk silently yields ``[]``.
    """
    if spec is None:
        return []
    types = getattr(spec, "types", None) or {}
    type_info = types.get(name)
    if type_info is None:
        return []
    values: List[str] = []

    def _collect(ti: Any) -> None:
        if ti is None:
            return
        ti_type = getattr(ti, "type", None)
        nested = getattr(ti, "nested", None)
        if ti_type is Literal and nested:
            for n in nested:
                literal_name = getattr(n, "name", None)
                if literal_name:
                    values.append(str(literal_name).strip("'\""))
        elif getattr(ti, "is_union", False) and nested:
            for n in nested:
                _collect(n)

    _collect(type_info)
    return values


def _import_completions(
    prefix: str,
    working_dir: str,
    *,
    api: Callable[..., Optional[List[Any]]],
    allow_kinds: Set[str],
    support_dotted: bool,
) -> List[Candidate]:
    """Dispatch library / resource / variables import completion.

    The prefix syntax selects the lookup mode:

    1. Plain identifier or empty: full discovery via ``api(None)``.
    2. Filesystem path (``/`` or ``\\``): listing of ``dir_part``.
    3. Dotted module path (only when ``support_dotted``): listing of
       ``base + "."``. Resource imports skip this since Robot treats
       ``common.resource`` as a filename, not a module path.
    """

    def _fetch(name: Optional[str]) -> List[Any]:
        if name is None:
            # Full discovery walks `sys.path` and the project tree —
            # cache it for the session so live-as-you-type stays snappy.
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


def _iter_keywords(context: Any = None) -> Iterator[Tuple[str, str]]:
    if context is None:
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


def _iter_variables(variables: Any = None, context: Any = None) -> Iterator[Tuple[str, str]]:
    # `variables` is a variable store (`.as_dict()`) — e.g. a paused frame's
    # scope, for frame-aware completion. Falls back to the context's variables.
    if variables is None:
        if context is None:
            context = EXECUTION_CONTEXTS.current
        if context is None:
            return
        variables = context.variables
    for decorated, value in variables.as_dict().items():
        name = str(decorated)
        if len(name) >= 3 and name[0] in _VALID_SIGILS and name[1] == "{" and name[-1] == "}":
            name = name[2:-1]
        yield name, _short_repr(value)


def _short_repr(value: object, max_len: int = 40) -> str:
    try:
        r = repr(value)
    except Exception:
        return ""
    if len(r) > max_len:
        return r[: max_len - 1] + "…"
    return r


def _filter_robot_normalised(items: Iterable[Tuple[str, str]], prefix: str) -> List[Candidate]:
    """Robot-normalised prefix filter over ``(name, detail)`` pairs.

    Dedupes by name (first-seen-wins, matching `_iter_keywords` /
    `_iter_variables` order) and sorts by label.
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
