"""Robot library / keyword runtime lookup helpers.

Backend-agnostic: both `ConsoleInterpreter` (plain) and
`PromptToolkitConsoleInterpreter` use these to resolve `.kw <name>`
and `.doc <library-or-resource>` dot-commands against the
currently-imported `_kw_store`. The richer completion machinery
(tokenize / candidates / CompletionContext / Candidate) is
prompt_toolkit-only and lives in `_pt.completion`.

Data is pulled straight from `EXECUTION_CONTEXTS.current`, which is
populated by the time the user hits Enter because the REPL runs
synchronously inside `suite.run()`.
"""

from typing import Any, Iterator, List, Optional, Tuple

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


def _current_kw_store() -> Optional[Any]:
    """The running namespace's keyword store, or ``None`` outside a run.

    `_kw_store` is a private attribute of Robot's `Namespace`; the
    ``getattr`` guards the one boundary where we reach into RF
    internals whose shape isn't part of its public API.
    """
    context = EXECUTION_CONTEXTS.current
    if context is None:
        return None
    return getattr(context.namespace, "_kw_store", None)


def lookup_keyword_doc(name: str) -> Optional[Any]:
    """Resolve ``name`` to a loaded keyword object, or ``None``.

    Matches Robot's case/whitespace/underscore-insensitive lookup
    (``Set Variable`` == ``set_variable``); library-defined keywords
    win over resource-defined ones on name collisions. The returned
    object is whatever ``_kw_store`` holds — typically a Robot runtime
    keyword with ``.name``, ``.args`` (``ArgumentSpec``), ``.doc``,
    ``.tags``, ``.source``. Callers should access fields defensively.
    """
    store = _current_kw_store()
    if store is None:
        return None
    target = _norm(name)
    if not target:
        return None
    for src in (*store.libraries.values(), *store.resources.values()):
        kw = _find_keyword_in_owner(src, target)
        if kw is not None:
            return kw
    return None


def lookup_keyword_owner(name: str) -> Optional[Tuple[Any, Any, bool]]:
    """Resolve ``name`` to ``(owner, keyword, is_resource)``, or ``None``.

    ``owner`` is the loaded library / resource instance that defines the
    keyword, ``keyword`` the runtime keyword object, and ``is_resource``
    tells which store section it came from. Libraries are searched
    before resources, so library keywords win on name collisions — the
    same precedence as `lookup_keyword_doc`. Callers use ``owner`` to
    render a rich `KeywordDoc` without reimporting it from disk.

    Both the plain keyword name (``Log``) and the explicit
    ``Owner.Keyword`` form (``BuiltIn.Log``) are accepted; the plain
    name is tried first so a keyword whose own name contains a dot still
    resolves, mirroring how Robot itself dispatches keyword calls.
    """
    store = _current_kw_store()
    if store is None:
        return None
    target = _norm(name)
    if not target:
        return None
    for owner in store.libraries.values():
        kw = _find_keyword_in_owner(owner, target)
        if kw is not None:
            return owner, kw, False
    for owner in store.resources.values():
        kw = _find_keyword_in_owner(owner, target)
        if kw is not None:
            return owner, kw, True
    if "." in name:
        return _lookup_explicit_keyword_owner(store, name)
    return None


def _lookup_explicit_keyword_owner(store: Any, full_name: str) -> Optional[Tuple[Any, Any, bool]]:
    """Resolve an explicit ``Owner.Keyword`` name against the store.

    Every ``owner . keyword`` split of ``full_name`` is tried (so both
    ``BuiltIn.Log`` and dotted owner/keyword names resolve), matching an
    owner by name in the library section before the resource section.
    """
    for owner_name, kw_name in _owner_and_keyword_splits(full_name):
        owner_target = owner_name.casefold()
        kw_target = _norm(kw_name)
        for owner in store.libraries.values():
            if str(owner.name).casefold() == owner_target:
                kw = _find_keyword_in_owner(owner, kw_target)
                if kw is not None:
                    return owner, kw, False
        for owner in store.resources.values():
            if str(owner.name).casefold() == owner_target:
                kw = _find_keyword_in_owner(owner, kw_target)
                if kw is not None:
                    return owner, kw, True
    return None


def _owner_and_keyword_splits(full_name: str) -> List[Tuple[str, str]]:
    """``Owner.Keyword`` partitions of ``full_name``, e.g.
    ``a.b.c`` → ``[(a, b.c), (a.b, c)]`` — same scheme Robot uses."""
    tokens = full_name.split(".")
    return [(".".join(tokens[:i]), ".".join(tokens[i:])) for i in range(1, len(tokens))]


def _find_keyword_in_owner(owner: Any, normalized_name: str) -> Optional[Any]:
    """First keyword on ``owner`` whose name folds to ``normalized_name``."""
    for kw in getattr(owner, _LIB_KEYWORDS_ATTR, ()) or ():
        kw_name = getattr(kw, "name", None)
        if kw_name and _norm(kw_name) == normalized_name:
            return kw
    return None


def iter_keyword_owners() -> Iterator[Tuple[str, bool, List[str]]]:
    """Yield ``(owner_name, is_resource, keyword_names)`` for each loaded
    library and resource, libraries first. ``keyword_names`` is sorted.
    Used to list / search what the session has imported.
    """
    store = _current_kw_store()
    if store is None:
        return
    for owner in store.libraries.values():
        yield str(owner.name), False, _keyword_names(owner)
    for owner in store.resources.values():
        yield str(owner.name), True, _keyword_names(owner)


def _keyword_names(owner: Any) -> List[str]:
    names = [str(kw.name) for kw in (getattr(owner, _LIB_KEYWORDS_ATTR, ()) or ()) if getattr(kw, "name", None)]
    return sorted(names)


def lookup_library(name: str) -> Optional[Any]:
    """The loaded library instance named ``name``, or ``None``.

    Looks only in the store's library section, so the result is always
    a Robot `TestLibrary` (RF >= 7) / `_BaseTestLibrary` (RF < 7) —
    suitable for
    `robotcode.robot.diagnostics.library_doc.get_library_doc_from_library`.
    """
    store = _current_kw_store()
    if store is None:
        return None
    return _find_owner_by_name(store.libraries.values(), name)


def lookup_resource(name: str) -> Optional[Any]:
    """The loaded resource instance named ``name``, or ``None``.

    Looks only in the store's resource section, so the result is a
    `UserLibrary` (RF < 7) / running `ResourceFile` (RF >= 7) —
    suitable for
    `robotcode.robot.diagnostics.library_doc.get_resource_doc_from_resource`.
    """
    store = _current_kw_store()
    if store is None:
        return None
    return _find_owner_by_name(store.resources.values(), name)


def _find_owner_by_name(owners: Any, name: str) -> Optional[Any]:
    """First owner in ``owners`` whose ``.name`` case-folds to ``name``."""
    target = name.casefold()
    if not target:
        return None
    for owner in owners:
        owner_name = owner.name
        if owner_name and str(owner_name).casefold() == target:
            return owner
    return None
