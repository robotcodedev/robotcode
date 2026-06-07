"""Tests for the REPL's Robot-aware completion logic.

The `tokenize()` half is pure-Python — no Robot context required, fast
to exercise across many edge cases. The `candidates_for()` half pulls
from `EXECUTION_CONTEXTS.current`, which is patched via a stand-in
namespace object so we don't need to spin up a full Robot suite.
"""

import os
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List

import pytest
from robot.running.context import EXECUTION_CONTEXTS

from robotcode.repl._keyword_lookup import (
    _LIB_KEYWORDS_ATTR,
    lookup_keyword_doc,
    lookup_keyword_owner,
    lookup_library,
    lookup_resource,
)
from robotcode.repl._pt.completion import (
    Candidate,
    CompletionContext,
    _clear_full_list_cache,
    _literal_values_for_named_arg,
    _spec_accepts_named_arg,
    candidates_for,
    candidates_for_rich,
    current_keyword_and_arg_index,
    current_named_arg_in_cell,
    find_cell_end,
    spec_arg_position,
    tokenize,
)
from robotcode.robot.utils import RF_VERSION


@pytest.fixture(autouse=True)
def _drop_full_list_cache() -> Iterable[None]:
    """`candidates_for()` caches `complete_*_import(None, …)` results
    for the REPL-session lifetime. Tests swap the api mock between
    invocations, so the cache must be flushed between them — otherwise
    later tests would see the first test's cached results."""
    _clear_full_list_cache()
    yield
    _clear_full_list_cache()


# ---------------------------------------------------------------------------
# tokenize() — cell detection, variable detection, special-form dispatch
# ---------------------------------------------------------------------------


def test_tokenize_first_cell_returns_keyword_context() -> None:
    ctx = tokenize("Lo", cursor=2)
    assert ctx.kind == "keyword"
    assert ctx.prefix == "Lo"
    assert ctx.replace_start == 0


def test_tokenize_empty_buffer_returns_keyword_context() -> None:
    ctx = tokenize("", cursor=0)
    assert ctx.kind == "keyword"
    assert ctx.prefix == ""
    assert ctx.replace_start == 0


def test_tokenize_two_space_separator_starts_second_cell() -> None:
    ctx = tokenize("Log    arg", cursor=10)
    assert ctx.kind == "argument"
    assert ctx.prefix == "arg"
    assert ctx.replace_start == 7  # right after the 4-space gap


def test_tokenize_tab_is_also_cell_separator() -> None:
    ctx = tokenize("Log\targ", cursor=7)
    assert ctx.kind == "argument"
    assert ctx.prefix == "arg"


def test_tokenize_single_space_keeps_first_cell() -> None:
    """`Log To Console` is a single keyword name — one space is *not* a separator."""
    ctx = tokenize("Log To Console", cursor=14)
    assert ctx.kind == "keyword"
    assert ctx.prefix == "Log To Console"
    assert ctx.replace_start == 0


def test_tokenize_import_library_routes_to_library_context() -> None:
    ctx = tokenize("Import Library    Coll", cursor=22)
    assert ctx.kind == "library"
    assert ctx.prefix == "Coll"


def test_tokenize_import_library_is_case_insensitive() -> None:
    ctx = tokenize("IMPORT LIBRARY    Coll", cursor=22)
    assert ctx.kind == "library"


def test_tokenize_import_resource_routes_to_resource_context() -> None:
    ctx = tokenize("Import Resource    ./common", cursor=27)
    assert ctx.kind == "resource"


def test_tokenize_import_variables_routes_to_variables_context() -> None:
    ctx = tokenize("Import Variables    creds.yaml", cursor=30)
    assert ctx.kind == "variables"


def test_tokenize_import_variables_is_case_insensitive() -> None:
    ctx = tokenize("IMPORT VARIABLES    vars.py", cursor=27)
    assert ctx.kind == "variables"


def test_tokenize_setting_aliases_route_argument_to_import_completion() -> None:
    # With the `>>>`-prompt opt-in, a bare alias routes its argument cell the
    # same way the `Import …` keyword does.
    assert tokenize("Library    Coll", cursor=15, setting_import_aliases=True).kind == "library"
    assert tokenize("Resource    ./common", cursor=20, setting_import_aliases=True).kind == "resource"
    assert tokenize("Variables    creds.yaml", cursor=23, setting_import_aliases=True).kind == "variables"
    # case-insensitive, like the `Import …` forms
    assert tokenize("library    Coll", cursor=15, setting_import_aliases=True).kind == "library"


def test_tokenize_setting_aliases_not_routed_without_optin() -> None:
    # Without the opt-in (e.g. the `(rdb)` prompt) a bare `Library` is an
    # ordinary keyword, so its second cell is a plain argument, not an import.
    assert tokenize("Library    Coll", cursor=15).kind == "argument"


def test_tokenize_return_assignment_keeps_keyword_completion() -> None:
    # A leading return-value assignment must not steal keyword completion from
    # the keyword cell. The `=` is optional and may sit on the last of several
    # targets; `${}`/`@{}`/`&{}` all count. (These forms work on every RF.)
    for buf in (
        "${result}=    Log To Con",
        "${result}    Log To Con",
        "${a}    ${b}=    Some Key",
        "@{items}=    Create Lis",
        "&{opts}=    Create Dic",
    ):
        assert tokenize(buf, len(buf)).kind == "keyword", buf


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="item assignment (${x}[0] =) requires Robot Framework >= 6.1")
def test_tokenize_item_assignment_keeps_keyword_completion() -> None:
    for buf in (
        "${list}[0]=    Set Variabl",
        "${dict}[key] =    Get Valu",
        "${res}[users][0] =    Get Use",
    ):
        assert tokenize(buf, len(buf)).kind == "keyword", buf


@pytest.mark.skipif(RF_VERSION < (7, 3), reason="variable type hints (${x: int}) require Robot Framework >= 7.3")
def test_tokenize_type_hint_assignment_keeps_keyword_completion() -> None:
    for buf in (
        "${x: int} =    Convert To In",
        "@{nums: int}    Create Lis",
    ):
        assert tokenize(buf, len(buf)).kind == "keyword", buf


def test_tokenize_return_assignment_then_keyword_args_route_normally() -> None:
    # After the assignment, the keyword and its args classify against the real
    # keyword — import routing and plain argument cells still work.
    lib = "${x}=    Import Library    Coll"
    assert tokenize(lib, len(lib)).kind == "library"
    alias = "${x}=    Library    Coll"
    assert tokenize(alias, len(alias), setting_import_aliases=True).kind == "library"
    arg = "${x}=    Log    msg"
    assert tokenize(arg, len(arg)).kind == "argument"


@pytest.mark.parametrize("sigil", ["$", "@", "&", "%"])
def test_tokenize_variable_opener_anywhere_in_cell(sigil: str) -> None:
    line = f"Log    Hello {sigil}{{world"
    ctx = tokenize(line, cursor=len(line))
    assert ctx.kind == "variable"
    assert ctx.prefix == "world"
    assert ctx.sigil == sigil
    # `replace_start` points at the sigil so candidates can swap in `${NAME}`.
    assert line[ctx.replace_start] == sigil


def test_tokenize_variable_empty_after_brace() -> None:
    ctx = tokenize("Log    ${", cursor=9)
    assert ctx.kind == "variable"
    assert ctx.prefix == ""
    assert ctx.sigil == "$"


def test_tokenize_closed_variable_is_not_completion_context() -> None:
    """`${X}` is already closed — typing past it goes back to argument-mode."""
    ctx = tokenize("Log    ${X} more", cursor=16)
    assert ctx.kind == "argument"
    assert ctx.prefix == "${X} more"


def test_tokenize_only_the_latest_unclosed_variable_wins() -> None:
    """Two variables in a row, the last one unclosed → that's the context."""
    ctx = tokenize("Log    ${A} ${B", cursor=15)
    assert ctx.kind == "variable"
    assert ctx.prefix == "B"


# ---------------------------------------------------------------------------
# candidates_for() — keyword sourcing, variable sourcing, filtering
# ---------------------------------------------------------------------------


def _fake_namespace(library_keywords: List[str], resource_keywords: List[str]) -> SimpleNamespace:
    """Build a Robot-context-shaped stub from plain string lists.

    Uses ``_LIB_KEYWORDS_ATTR`` so the fixture mirrors whichever
    attribute name the running Robot version uses (``keywords`` on
    7.0+, ``handlers`` on 5/6) — same dispatch as the production code.
    """

    def _lib(name: str, keyword_names: List[str]) -> SimpleNamespace:
        return SimpleNamespace(name=name, **{_LIB_KEYWORDS_ATTR: [SimpleNamespace(name=n) for n in keyword_names]})

    libraries = {"BuiltIn": _lib("BuiltIn", library_keywords)}

    class _FakeResources:
        def values(self) -> Iterable[SimpleNamespace]:
            return [_lib("MyResource", resource_keywords)]

    return SimpleNamespace(
        namespace=SimpleNamespace(_kw_store=SimpleNamespace(libraries=libraries, resources=_FakeResources())),
        variables=SimpleNamespace(as_dict=dict),
    )


def _patch_context(monkeypatch: pytest.MonkeyPatch, ctx_obj: object) -> None:
    """Pretend `EXECUTION_CONTEXTS.current` returns `ctx_obj`."""
    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [ctx_obj])


def test_candidates_for_keyword_returns_loaded_library_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log", "Log To Console", "Set Variable"], []))
    out = candidates_for(CompletionContext("keyword", "Lo", 0))
    assert "Log" in out
    assert "Log To Console" in out
    # Robot's normalised matching: 'Lo' should NOT match 'Set Variable'.
    assert "Set Variable" not in out


def test_candidates_for_keyword_includes_resource_keywords(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], ["Open Browser", "Login With Credentials"]))
    out = candidates_for(CompletionContext("keyword", "Open", 0))
    assert "Open Browser" in out


def test_candidates_for_keyword_case_and_whitespace_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log To Console"], []))
    out = candidates_for(CompletionContext("keyword", "logtoco", 0))
    assert "Log To Console" in out


def test_candidates_for_keyword_dedupes_across_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Helper"], ["Helper"]))
    out = candidates_for(CompletionContext("keyword", "Helper", 0))
    assert out.count("Helper") == 1


def test_candidates_for_keyword_empty_when_no_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [])
    out = candidates_for(CompletionContext("keyword", "anything", 0))
    assert out == []


def test_candidates_for_keyword_includes_setting_aliases_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    # The `>>>` prompt opts in via `include_setting_aliases=True`, so the
    # Settings-style aliases show up as keyword candidates alongside the real
    # `Import …` keywords, with a detail pointing at the canonical keyword.
    _patch_context(monkeypatch, _fake_namespace(["Import Library", "Log"], []))
    cands = candidates_for_rich(CompletionContext("keyword", "Lib", 0), include_setting_aliases=True)
    by_label = {c.label: c.detail for c in cands}
    assert "Library" in by_label
    assert "Import Library" in by_label["Library"]


def test_candidates_for_keyword_setting_aliases_match_their_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace([], []))
    res = [c.label for c in candidates_for_rich(CompletionContext("keyword", "Res", 0), include_setting_aliases=True)]
    var = [c.label for c in candidates_for_rich(CompletionContext("keyword", "Var", 0), include_setting_aliases=True)]
    assert "Resource" in res
    assert "Variables" in var


def test_candidates_for_keyword_omits_setting_aliases_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without the opt-in (e.g. the `(rdb)` prompt) the aliases are NOT offered —
    # they don't apply there.
    _patch_context(monkeypatch, _fake_namespace(["Import Library", "Log"], []))
    labels = [c.label for c in candidates_for_rich(CompletionContext("keyword", "Lib", 0))]
    assert "Library" not in labels


def test_candidates_for_variable_strips_wrapper_and_re_wraps(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_namespace([], [])
    fake.variables.as_dict = lambda: {
        "${TEST_NAME}": "x",
        "${SUITE_NAME}": "y",
        "@{LIST}": [1, 2],
    }
    _patch_context(monkeypatch, fake)
    out = candidates_for(CompletionContext("variable", "TEST", 0, sigil="$"))
    # Variable candidates come back wrapped in the user's sigil + braces.
    assert "${TEST_NAME}" in out
    assert "${SUITE_NAME}" not in out
    # List/dict variables get rewrapped with the *user's* sigil, not their original.
    out_at = candidates_for(CompletionContext("variable", "LIST", 0, sigil="@"))
    assert "@{LIST}" in out_at


def test_candidates_for_env_variable_sources_from_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    """`%{...}` is an *environment* variable in Robot — sourced from
    ``os.environ``, NOT the suite's variable scope."""
    fake = _fake_namespace([], [])
    # A Robot-scope variable that must NOT appear in `%{}` completion —
    # picked with a name that's vanishingly unlikely to exist in
    # `os.environ`, so the negative assertion can't be confused by a
    # real environment hit.
    fake.variables.as_dict = lambda: {"${ROBOTCODE_TEST_ONLY_IN_SCOPE}": "x"}
    _patch_context(monkeypatch, fake)

    monkeypatch.setenv("ROBOTCODE_TEST_ENVVAR", "x")
    monkeypatch.setenv("ROBOTCODE_TEST_OTHER", "y")
    monkeypatch.delenv("ROBOTCODE_TEST_ONLY_IN_SCOPE", raising=False)

    out = candidates_for(CompletionContext("variable", "ROBOTCODE_TEST_", 0, sigil="%"))
    assert "%{ROBOTCODE_TEST_ENVVAR}" in out
    assert "%{ROBOTCODE_TEST_OTHER}" in out
    assert "%{ROBOTCODE_TEST_ONLY_IN_SCOPE}" not in out  # Robot scope must not leak into env-var lookup
    assert os.environ.get("ROBOTCODE_TEST_ONLY_IN_SCOPE") is None  # guard the negative assertion above


def test_candidates_for_argument_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    out = candidates_for(CompletionContext("argument", "anything", 0))
    assert out == []


# ---------------------------------------------------------------------------
# candidates_for_rich — Stage 6 doc-hints / display_meta sourcing
# ---------------------------------------------------------------------------


def _fake_namespace_with_docs(library_keywords: "List[tuple[str, str]]") -> SimpleNamespace:
    """Like `_fake_namespace` but each keyword carries a `short_doc` /
    `shortdoc` attribute (depending on the RF version mock-target)."""
    from robotcode.repl._pt.completion import _KW_SHORT_DOC_ATTR

    def _lib(name: str, kws: "List[tuple[str, str]]") -> SimpleNamespace:
        return SimpleNamespace(
            name=name,
            **{_LIB_KEYWORDS_ATTR: [SimpleNamespace(name=n, **{_KW_SHORT_DOC_ATTR: d}) for n, d in kws]},
        )

    libraries = {"BuiltIn": _lib("BuiltIn", library_keywords)}

    class _FakeResources:
        def values(self) -> Iterable[SimpleNamespace]:
            return []

    return SimpleNamespace(
        namespace=SimpleNamespace(_kw_store=SimpleNamespace(libraries=libraries, resources=_FakeResources())),
        variables=SimpleNamespace(as_dict=dict),
    )


def test_candidates_for_rich_keyword_includes_short_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(
        monkeypatch,
        _fake_namespace_with_docs(
            [
                ("Log", "Log a message with the given level"),
                ("Log To Console", "Log a message to the console"),
            ]
        ),
    )
    out = candidates_for_rich(CompletionContext("keyword", "Lo", 0))
    by_label = {c.label: c.detail for c in out}
    assert by_label.get("Log") == "Log a message with the given level"
    assert by_label.get("Log To Console") == "Log a message to the console"


def test_candidates_for_rich_keyword_handles_missing_short_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    """A keyword without a docstring must return an empty `detail`,
    not error out."""
    _patch_context(monkeypatch, _fake_namespace_with_docs([("Log", "")]))
    out = candidates_for_rich(CompletionContext("keyword", "Log", 0))
    assert out == [Candidate(label="Log", detail="")]


def test_candidates_for_rich_variable_includes_value_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_namespace([], [])
    fake.variables.as_dict = lambda: {"${TEST_NAME}": "Smoke", "${COUNT}": 42}
    _patch_context(monkeypatch, fake)
    out = candidates_for_rich(CompletionContext("variable", "TEST", 0, sigil="$"))
    assert any(c.label == "${TEST_NAME}" and c.detail == "'Smoke'" for c in out)


def test_candidates_for_rich_variable_value_truncated_at_40_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Huge values mustn't blow out the popup width."""
    fake = _fake_namespace([], [])
    fake.variables.as_dict = lambda: {"${BIG}": "x" * 500}
    _patch_context(monkeypatch, fake)
    out = candidates_for_rich(CompletionContext("variable", "BIG", 0, sigil="$"))
    [cand] = [c for c in out if c.label == "${BIG}"]
    assert len(cand.detail) <= 40


def test_candidates_for_rich_env_variable_uses_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _fake_namespace([], [])
    _patch_context(monkeypatch, fake)
    monkeypatch.setenv("ROBOTCODE_TEST_RICH_ENV", "hello")
    out = candidates_for_rich(CompletionContext("variable", "ROBOTCODE_TEST_RICH", 0, sigil="%"))
    [cand] = [c for c in out if c.label == "%{ROBOTCODE_TEST_RICH_ENV}"]
    assert cand.detail == "'hello'"


def test_find_cell_end_stops_at_double_space() -> None:
    """`Log Many  arg` — cell end is at the `  ` cell separator."""
    text = "Log Many  arg"
    assert find_cell_end(text, 0) == 8  # `Log Many` is 8 chars, then `  `


def test_find_cell_end_stops_at_tab() -> None:
    """Tab is also a Robot cell separator."""
    text = "Log\targ"
    assert find_cell_end(text, 0) == 3


def test_find_cell_end_stops_at_newline() -> None:
    """A line ends at `\\n`; the next cell start lives on the next line."""
    text = "Log\nLog    arg"
    assert find_cell_end(text, 0) == 3


def test_find_cell_end_reaches_eot_when_no_separator() -> None:
    """A single-cell line ends at end-of-text."""
    text = "Log To Console"
    assert find_cell_end(text, 0) == len(text)


def test_find_cell_end_from_mid_cell() -> None:
    """Starting from inside a cell scans forward to that cell's end."""
    text = "Log To Console  arg"
    # Cursor at position 3 (after `Log`), should still find the `  ` at 14.
    assert find_cell_end(text, 3) == 14


def test_candidates_for_rich_library_import_carries_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    _patch_library_import(
        monkeypatch,
        {
            None: [
                CompleteResult("Collections", CompleteResultKind.MODULE_INTERNAL),
                CompleteResult("SeleniumLibrary", CompleteResultKind.MODULE),
            ]
        },
    )
    out = candidates_for_rich(CompletionContext("library", "Coll", 0))
    [cand] = [c for c in out if c.label == "Collections"]
    assert cand.detail == "MODULE_INTERNAL"


# ---------------------------------------------------------------------------
# Library import — plain identifier, dotted module path, filesystem path.
# `complete_library_import` is stubbed per-test so we can assert on the
# `name=...` argument the implementation passes to Robot.
# ---------------------------------------------------------------------------


def _patch_import_api(
    monkeypatch: pytest.MonkeyPatch,
    api_name: str,
    behaviour: Dict[Any, List[Any]],
) -> List[object]:
    """Replace one of the three `complete_*_import` Robot APIs with a
    per-name lookup table.

    Patches in `_completion`'s namespace — not the source module — so
    the indirection works whether `_completion` does `from … import …`
    or `import … as …`. Returns a `calls` list — every `name`
    argument the implementation passes is appended in order, so tests
    can verify *what* the completion code asked Robot for.

    ``api_name`` is one of ``"complete_library_import"``,
    ``"complete_resource_import"``, ``"complete_variables_import"``.
    """
    calls: List[object] = []

    def fake(name: object, **_kwargs: object) -> List[Any]:
        calls.append(name)
        return behaviour.get(name, [])

    monkeypatch.setattr(f"robotcode.repl._pt.completion.{api_name}", fake)
    return calls


def _patch_library_import(monkeypatch: pytest.MonkeyPatch, behaviour: Dict[Any, List[Any]]) -> List[object]:
    """Backwards-compat shim — most existing library tests use this name."""
    return _patch_import_api(monkeypatch, "complete_library_import", behaviour)


def test_candidates_for_library_plain_prefix_matches_installed_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`Coll` → completes against the full installed-module list."""
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    calls = _patch_library_import(
        monkeypatch,
        {
            None: [
                CompleteResult("Collections", CompleteResultKind.MODULE_INTERNAL),
                CompleteResult("SeleniumLibrary", CompleteResultKind.MODULE),
                CompleteResult("Log", CompleteResultKind.KEYWORD),  # wrong kind, must be filtered out
            ]
        },
    )
    out = candidates_for(CompletionContext("library", "Coll", 0))
    assert "Collections" in out
    assert "SeleniumLibrary" not in out  # prefix-filtered
    assert "Log" not in out  # kind-filtered
    # Plain prefix → only the no-arg installed-module list is queried.
    assert calls == [None]


def test_full_discovery_result_is_cached_across_invocations(monkeypatch: pytest.MonkeyPatch) -> None:
    """`api(None, …)` is walked once per session — not once per keystroke."""
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    calls = _patch_library_import(
        monkeypatch,
        {None: [CompleteResult("Collections", CompleteResultKind.MODULE_INTERNAL)]},
    )

    # Three different "live-as-you-type" keystrokes — `""`, `"C"`, `"Co"` —
    # all land in the `name=None` branch (empty + plain prefix). prompt_toolkit
    # in live-completion mode would call us once per keystroke; the api must
    # still only be hit *once*.
    candidates_for(CompletionContext("library", "", 0))
    candidates_for(CompletionContext("library", "C", 0))
    candidates_for(CompletionContext("library", "Co", 0))
    assert calls == [None], f"expected exactly one full-discovery call, got: {calls}"


def test_candidates_for_library_empty_prefix_returns_full_list(monkeypatch: pytest.MonkeyPatch) -> None:
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    _patch_library_import(
        monkeypatch,
        {
            None: [
                CompleteResult("Collections", CompleteResultKind.MODULE_INTERNAL),
                CompleteResult("SeleniumLibrary", CompleteResultKind.MODULE),
            ]
        },
    )
    out = candidates_for(CompletionContext("library", "", 0))
    assert "Collections" in out
    assert "SeleniumLibrary" in out


def test_candidates_for_library_dotted_path_stitches_full_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`robot.libraries.Coll<Tab>` → `robot.libraries.Collections`.

    Robot's `complete_library_import("robot.libraries.")` yields bare
    submodule labels (`Collections`); the completer prepends the
    `robot.libraries.` head so the candidate is a drop-in cell.
    """
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    calls = _patch_library_import(
        monkeypatch,
        {
            "robot.libraries.": [
                CompleteResult("Collections", CompleteResultKind.MODULE),
                CompleteResult("Dialogs", CompleteResultKind.MODULE),
                CompleteResult("OperatingSystem", CompleteResultKind.MODULE),
            ]
        },
    )
    out = candidates_for(CompletionContext("library", "robot.libraries.Coll", 0))
    assert out == ["robot.libraries.Collections"]
    # Confirm we asked Robot specifically for submodules of `robot.libraries`.
    assert "robot.libraries." in calls
    # And we did *not* fall back to the no-arg "all modules" query —
    # would dump irrelevant top-level noise.
    assert None not in calls


def test_candidates_for_library_dotted_empty_partial_lists_all_submodules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`robot.libraries.<Tab>` (nothing after the dot) → list every submodule."""
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    _patch_library_import(
        monkeypatch,
        {
            "robot.libraries.": [
                CompleteResult("Collections", CompleteResultKind.MODULE),
                CompleteResult("OperatingSystem", CompleteResultKind.MODULE),
            ]
        },
    )
    out = candidates_for(CompletionContext("library", "robot.libraries.", 0))
    assert "robot.libraries.Collections" in out
    assert "robot.libraries.OperatingSystem" in out


def test_candidates_for_library_filesystem_path_keeps_directory_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`./libs/My<Tab>` → `./libs/MyLib.py` (the dir-part stays attached).

    Robot's discovery APIs are *directory listings* — we pass them the dir
    part (`./libs/`) and filter by the partial filename (`My`) ourselves.
    """
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    calls = _patch_library_import(
        monkeypatch,
        {
            "./libs/": [
                CompleteResult("MyLib.py", CompleteResultKind.FILE),
                CompleteResult("MyOtherLib", CompleteResultKind.FOLDER),
                CompleteResult("UnrelatedLib.py", CompleteResultKind.FILE),  # filtered by partial
            ]
        },
    )
    out = candidates_for(CompletionContext("library", "./libs/My", 0))
    assert "./libs/MyLib.py" in out
    assert "./libs/MyOtherLib" in out
    assert "UnrelatedLib.py" not in out
    assert "./libs/UnrelatedLib.py" not in out
    # Robot is asked for the directory listing, not the partial-name match.
    assert "./libs/" in calls
    assert None not in calls  # no top-level scan in path-mode


def test_candidates_for_library_windows_path_separator_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    _patch_library_import(
        monkeypatch,
        {
            "libs\\": [CompleteResult("MyLib.py", CompleteResultKind.FILE)],
        },
    )
    out = candidates_for(CompletionContext("library", "libs\\My", 0))
    assert "libs\\MyLib.py" in out


def test_candidates_for_resource_uses_complete_resource_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: resource completion used to share Robot's library-import API,
    which returned every Python module on the system. Resource completion now
    delegates to `complete_resource_import`, which only emits `.robot` / `.resource`
    files + folders. The top-level call matches the language server's pattern —
    `api(None, ...)` — so Robot's full discovery (including any resource files
    shipped by installed packages) reaches the user."""
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    library_calls = _patch_library_import(monkeypatch, {})
    resource_calls = _patch_import_api(
        monkeypatch,
        "complete_resource_import",
        {
            None: [
                CompleteResult("common.resource", CompleteResultKind.RESOURCE),
                CompleteResult("subdir", CompleteResultKind.FOLDER),
            ]
        },
    )
    out = candidates_for(CompletionContext("resource", "", 0))
    assert "common.resource" in out
    assert "subdir" in out
    # Crucially: the resource-completion path must NOT touch the library API.
    assert library_calls == []
    # And must ask Robot using the language-server pattern — name=None.
    assert resource_calls == [None]


def test_candidates_for_resource_path_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Import Resource    ./res/<Tab>` → list contents of `./res/`."""
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    _patch_import_api(
        monkeypatch,
        "complete_resource_import",
        {
            "./res/": [
                CompleteResult("common.resource", CompleteResultKind.RESOURCE),
                CompleteResult("subdir", CompleteResultKind.FOLDER),
            ],
        },
    )
    out = candidates_for(CompletionContext("resource", "./res/", 0))
    assert "./res/common.resource" in out
    assert "./res/subdir" in out


def test_candidates_for_resource_does_not_treat_dots_as_module_separators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`common.resource` is a *filename*, not a dotted module path. The
    library-style dotted-path mode is disabled for resources — matching the
    language server, which only uses `[/, os.sep]` as split chars for
    resource imports."""
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    calls = _patch_import_api(
        monkeypatch,
        "complete_resource_import",
        {
            None: [
                CompleteResult("common.resource", CompleteResultKind.RESOURCE),
                CompleteResult("common.robot", CompleteResultKind.RESOURCE),
            ],
        },
    )
    out = candidates_for(CompletionContext("resource", "common", 0))
    assert "common.resource" in out
    assert "common.robot" in out
    # No dotted-path split — Robot is queried with name=None (full
    # discovery), not with name="common." (would imply submodule scan).
    assert calls == [None]
    assert "common." not in calls


def test_candidates_for_variables_uses_complete_variables_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Import Variables` has its own Robot API with its own file extensions
    (`.py`, `.yaml`, `.yml`, `.json`). Top-level matches the language server
    pattern — `api(None, ...)` — for parity with library / resource."""
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    library_calls = _patch_library_import(monkeypatch, {})
    variables_calls = _patch_import_api(
        monkeypatch,
        "complete_variables_import",
        {
            None: [
                CompleteResult("creds.yaml", CompleteResultKind.FILE),
                CompleteResult("env_vars.py", CompleteResultKind.FILE),
                CompleteResult("envs", CompleteResultKind.FOLDER),
            ]
        },
    )
    out = candidates_for(CompletionContext("variables", "", 0))
    assert "creds.yaml" in out
    assert "env_vars.py" in out
    assert "envs" in out
    assert library_calls == []
    assert variables_calls == [None]


def test_candidates_for_variables_path_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Import Variables    ./vars/<Tab>` → list YAML/JSON/PY files in `./vars/`."""
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    _patch_import_api(
        monkeypatch,
        "complete_variables_import",
        {
            "./vars/": [
                CompleteResult("staging.yaml", CompleteResultKind.FILE),
                CompleteResult("prod.json", CompleteResultKind.FILE),
            ],
        },
    )
    out = candidates_for(CompletionContext("variables", "./vars/", 0))
    assert "./vars/staging.yaml" in out
    assert "./vars/prod.json" in out


def test_candidates_for_variables_dotted_module_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Import Variables    myproject.config.<Tab>` lists submodules.

    The LS treats variables imports like library imports — dots are
    module-path separators when no `/` is in the input.
    """
    from robotcode.robot.diagnostics.library_doc import CompleteResult, CompleteResultKind

    _patch_import_api(
        monkeypatch,
        "complete_variables_import",
        {
            "myproject.config.": [
                CompleteResult("dev", CompleteResultKind.MODULE),
                CompleteResult("staging", CompleteResultKind.MODULE),
                CompleteResult("prod", CompleteResultKind.MODULE),
            ]
        },
    )
    out = candidates_for(CompletionContext("variables", "myproject.config.dev", 0))
    assert out == ["myproject.config.dev"]


# ---------------------------------------------------------------------------
# current_keyword_and_arg_index — cursor-position → (keyword, arg_idx)
# ---------------------------------------------------------------------------


def test_current_kw_and_arg_in_first_cell_returns_none() -> None:
    assert current_keyword_and_arg_index("Log", 3) is None


def test_current_kw_and_arg_returns_arg0_in_first_arg_cell() -> None:
    assert current_keyword_and_arg_index("Log    hello", 9) == ("Log", 0)


def test_current_kw_and_arg_walks_cells_for_second_arg() -> None:
    assert current_keyword_and_arg_index("Log    hello    level=DEBUG", 23) == ("Log", 1)


def test_current_kw_and_arg_tab_separator_counts_as_cell() -> None:
    assert current_keyword_and_arg_index("Log\thello", 6) == ("Log", 0)


def test_current_kw_and_arg_empty_keyword_returns_none() -> None:
    """Leading whitespace produces an empty first cell — that's not a keyword."""
    assert current_keyword_and_arg_index("    hello", 8) is None


def test_current_kw_and_arg_stops_at_logical_line_boundary() -> None:
    """Cursor on the second line of a multi-line buffer reports the
    second line's cells, not the buffer's accumulated cells."""
    buf = "FOR    ${i}    IN RANGE    3\n    Log    hello"
    pos = len(buf)
    assert current_keyword_and_arg_index(buf, pos) == ("Log", 0)


def test_current_kw_and_arg_skips_return_value_assignment() -> None:
    # A leading `${x}=` assignment must anchor on the keyword, not the target —
    # otherwise the status-bar argument hint resolves the wrong keyword.
    s = "${r}=    Log    hello"
    assert current_keyword_and_arg_index(s, len(s)) == ("Log", 0)
    # still in the keyword cell (no argument yet) → no hint
    k = "${r}=    Log"
    assert current_keyword_and_arg_index(k, len(k)) is None
    # several targets, the last carrying the `=`
    m = "${a}    ${b}=    Run Keyword    x"
    assert current_keyword_and_arg_index(m, len(m)) == ("Run Keyword", 0)


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="item assignment (${x}[0] =) requires Robot Framework >= 6.1")
def test_current_kw_and_arg_skips_item_assignment() -> None:
    i = "${list}[0] =    Log    hi"
    assert current_keyword_and_arg_index(i, len(i)) == ("Log", 0)


@pytest.mark.skipif(RF_VERSION < (7, 3), reason="variable type hints (${x: int}) require Robot Framework >= 7.3")
def test_current_kw_and_arg_skips_type_hint_assignment() -> None:
    t = "${x: int} =    Set Variable    42"
    assert current_keyword_and_arg_index(t, len(t)) == ("Set Variable", 0)


# ---------------------------------------------------------------------------
# lookup_keyword_doc / lookup_library / lookup_resource — _kw_store walk
# ---------------------------------------------------------------------------


def test_lookup_keyword_doc_finds_loaded_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log", "Set Variable"], []))
    kw = lookup_keyword_doc("Log")
    assert kw is not None
    assert kw.name == "Log"


def test_lookup_keyword_doc_normalises_case_and_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Set Variable"], []))
    assert lookup_keyword_doc("set variable") is not None
    assert lookup_keyword_doc("SetVariable") is not None
    assert lookup_keyword_doc("set_variable") is not None


def test_lookup_keyword_doc_returns_none_for_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    assert lookup_keyword_doc("Definitely Not A Keyword") is None


def test_lookup_keyword_doc_returns_none_without_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(EXECUTION_CONTEXTS, "_contexts", [])
    assert lookup_keyword_doc("Log") is None


def test_lookup_keyword_doc_walks_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace([], ["Custom Keyword"]))
    kw = lookup_keyword_doc("Custom Keyword")
    assert kw is not None
    assert kw.name == "Custom Keyword"


def test_lookup_library_matches_loaded_library(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_fake_namespace` names its library `BuiltIn` — case-insensitive match."""
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    lib = lookup_library("builtin")
    assert lib is not None
    assert lib.name == "BuiltIn"


def test_lookup_library_returns_none_for_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    assert lookup_library("ThisLibIsNotLoaded") is None


def test_lookup_library_does_not_match_resource(monkeypatch: pytest.MonkeyPatch) -> None:
    """`MyResource` lives in the resource section, not the library section."""
    _patch_context(monkeypatch, _fake_namespace([], ["Custom Keyword"]))
    assert lookup_library("MyResource") is None


def test_lookup_resource_matches_loaded_resource(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_fake_namespace` names its resource `MyResource` — case-insensitive match."""
    _patch_context(monkeypatch, _fake_namespace([], ["Custom Keyword"]))
    res = lookup_resource("myresource")
    assert res is not None
    assert res.name == "MyResource"


def test_lookup_resource_does_not_match_library(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    assert lookup_resource("BuiltIn") is None


def test_lookup_keyword_owner_finds_library_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    found = lookup_keyword_owner("Log")
    assert found is not None
    owner, kw, is_resource = found
    assert owner.name == "BuiltIn"
    assert kw.name == "Log"
    assert is_resource is False


def test_lookup_keyword_owner_flags_resource_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace([], ["Custom Keyword"]))
    found = lookup_keyword_owner("Custom Keyword")
    assert found is not None
    owner, _kw, is_resource = found
    assert owner.name == "MyResource"
    assert is_resource is True


def test_lookup_keyword_owner_library_wins_over_resource(monkeypatch: pytest.MonkeyPatch) -> None:
    """A name defined in both sections resolves to the library, matching
    `lookup_keyword_doc`'s precedence."""
    _patch_context(monkeypatch, _fake_namespace(["Shared"], ["Shared"]))
    found = lookup_keyword_owner("Shared")
    assert found is not None
    owner, _kw, is_resource = found
    assert owner.name == "BuiltIn"
    assert is_resource is False


def test_lookup_keyword_owner_resolves_explicit_library_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """`.kw BuiltIn.Log` — explicit ``Owner.Keyword`` form."""
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    found = lookup_keyword_owner("BuiltIn.Log")
    assert found is not None
    owner, kw, is_resource = found
    assert owner.name == "BuiltIn"
    assert kw.name == "Log"
    assert is_resource is False


def test_lookup_keyword_owner_resolves_explicit_resource_name(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace([], ["Custom Keyword"]))
    found = lookup_keyword_owner("MyResource.Custom Keyword")
    assert found is not None
    owner, kw, is_resource = found
    assert owner.name == "MyResource"
    assert kw.name == "Custom Keyword"
    assert is_resource is True


def test_lookup_keyword_owner_explicit_name_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    found = lookup_keyword_owner("builtin.log")
    assert found is not None
    assert found[0].name == "BuiltIn"


def test_lookup_keyword_owner_explicit_unknown_owner_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    assert lookup_keyword_owner("Nope.Log") is None


def test_lookup_keyword_owner_returns_none_for_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_context(monkeypatch, _fake_namespace(["Log"], []))
    assert lookup_keyword_owner("Definitely Not A Keyword") is None


# ---------------------------------------------------------------------------
# Embedded-argument completion — `name=<partial>` in an argument cell
# ---------------------------------------------------------------------------


def _kw_with_named_arg(
    name: str,
    arg_name: str,
    *,
    literals: Any = None,
    var_named: Any = None,
) -> Any:
    """Stand-in for a runtime keyword with `kw.args` ArgumentSpec.

    `literals=None` builds a spec where `arg_name` exists but carries
    no Literal type (testing the RF 5/6 fallback). `literals=[...]`
    builds a `TypeInfo` shape with `type=Literal` so the runtime
    literal-extraction path yields the listed values.
    """
    from typing import Literal as _Literal

    types: Dict[str, Any] = {}
    if literals is not None:
        # Robot's runtime TypeInfo stores nested literal names *with*
        # surrounding quotes — `_literal_values_for_named_arg` strips
        # them, so we mirror that here for fidelity.
        nested = [SimpleNamespace(name=f"'{v}'") for v in literals]
        types[arg_name] = SimpleNamespace(type=_Literal, nested=nested, is_union=False)
    spec = SimpleNamespace(
        positional_or_named=(arg_name,),
        named_only=(),
        var_named=var_named,
        types=types,
    )
    return SimpleNamespace(name=name, args=spec)


def _patch_kw_lookup(monkeypatch: pytest.MonkeyPatch, kws_by_name: Dict[str, Any]) -> None:
    """Replace `_completion.lookup_keyword_doc` with a dict lookup.

    Both `tokenize` (for verifying the arg name is real) and
    `candidates_for_rich` (for extracting Literal values) go through
    `lookup_keyword_doc`, so patching once covers both paths."""
    import robotcode.repl._pt.completion as completion_mod

    monkeypatch.setattr(completion_mod, "lookup_keyword_doc", lambda name: kws_by_name.get(name))


def test_tokenize_detects_named_arg_value_when_arg_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_kw_lookup(monkeypatch, {"Log": _kw_with_named_arg("Log", "level")})
    ctx = tokenize("Log    level=DE", cursor=15)
    assert ctx.kind == "named_arg_value"
    assert ctx.keyword_name == "Log"
    assert ctx.arg_name == "level"
    assert ctx.prefix == "DE"


def test_tokenize_named_arg_empty_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cursor right after `=` → empty prefix, ready to receive a literal."""
    _patch_kw_lookup(monkeypatch, {"Log": _kw_with_named_arg("Log", "level")})
    ctx = tokenize("Log    level=", cursor=13)
    assert ctx.kind == "named_arg_value"
    assert ctx.arg_name == "level"
    assert ctx.prefix == ""


def test_tokenize_name_equals_value_for_unknown_arg_is_plain_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    """`Log    foo=bar` — `foo` is NOT a Log argument, so Robot would
    pass `foo=bar` as a literal positional value. Tokenize mirrors
    that classification: `argument`, not `named_arg_value`."""
    _patch_kw_lookup(monkeypatch, {"Log": _kw_with_named_arg("Log", "level")})
    ctx = tokenize("Log    foo=bar", cursor=14)
    assert ctx.kind == "argument"


def test_tokenize_name_equals_value_for_unknown_keyword_is_plain_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    """No matching keyword in the live context → fall back to plain
    argument context (can't verify, so don't assume)."""
    _patch_kw_lookup(monkeypatch, {})
    ctx = tokenize("UnknownKW    foo=bar", cursor=20)
    assert ctx.kind == "argument"


def test_tokenize_kwargs_keyword_accepts_any_named_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    """A keyword with `**kwargs` accepts arbitrary `name=value` pairs,
    so even an unfamiliar name is a valid named-arg context."""
    _patch_kw_lookup(
        monkeypatch,
        {"Kwargs Kw": _kw_with_named_arg("Kwargs Kw", "known", var_named="kwargs")},
    )
    ctx = tokenize("Kwargs Kw    anything=42", cursor=24)
    assert ctx.kind == "named_arg_value"
    assert ctx.arg_name == "anything"


def test_tokenize_argument_without_equals_stays_plain_argument() -> None:
    ctx = tokenize("Log    hello", cursor=12)
    assert ctx.kind == "argument"


def test_candidates_for_rich_named_arg_returns_filtered_literals(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_kw_lookup(
        monkeypatch,
        {"Log": _kw_with_named_arg("Log", "level", literals=["DEBUG", "INFO", "WARN", "ERROR"])},
    )
    ctx = tokenize("Log    level=DE", cursor=15)
    out = candidates_for_rich(ctx)
    assert [c.label for c in out] == ["DEBUG"]


def test_candidates_for_rich_named_arg_case_insensitive_match(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_kw_lookup(monkeypatch, {"Log": _kw_with_named_arg("Log", "level", literals=["DEBUG", "INFO"])})
    ctx = tokenize("Log    level=de", cursor=15)
    out = candidates_for_rich(ctx)
    assert [c.label for c in out] == ["DEBUG"]


def test_candidates_for_rich_named_arg_empty_prefix_returns_all(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_kw_lookup(
        monkeypatch,
        {"Log": _kw_with_named_arg("Log", "level", literals=["DEBUG", "INFO", "WARN"])},
    )
    ctx = tokenize("Log    level=", cursor=13)
    out = candidates_for_rich(ctx)
    assert {c.label for c in out} == {"DEBUG", "INFO", "WARN"}


def test_candidates_for_rich_named_arg_no_literal_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """Argument exists but has no `Literal[...]` type → no candidates,
    no crash. Covers RF 5/6 too: `spec.types` there stores bare classes
    that the TypeInfo walk simply doesn't match on."""
    _patch_kw_lookup(monkeypatch, {"Set Variable": _kw_with_named_arg("Set Variable", "value", literals=None)})
    ctx = tokenize("Set Variable    value=foo", cursor=25)
    # Tokenize still classifies as named_arg_value (arg name is valid)
    # but the literal-value lookup finds nothing.
    assert ctx.kind == "named_arg_value"
    assert candidates_for_rich(ctx) == []


# ---------------------------------------------------------------------------
# `_spec_accepts_named_arg` — direct unit tests against the helper
# ---------------------------------------------------------------------------


def test_spec_accepts_named_arg_in_positional_or_named() -> None:
    spec = SimpleNamespace(positional_or_named=("level", "msg"), named_only=(), var_named=None)
    assert _spec_accepts_named_arg(spec, "level") is True
    assert _spec_accepts_named_arg(spec, "msg") is True
    assert _spec_accepts_named_arg(spec, "unknown") is False


def test_spec_accepts_named_arg_in_named_only() -> None:
    spec = SimpleNamespace(positional_or_named=(), named_only=("flag",), var_named=None)
    assert _spec_accepts_named_arg(spec, "flag") is True
    assert _spec_accepts_named_arg(spec, "other") is False


def test_spec_accepts_named_arg_with_var_named_accepts_anything() -> None:
    spec = SimpleNamespace(positional_or_named=(), named_only=(), var_named="kwargs")
    assert _spec_accepts_named_arg(spec, "whatever_name") is True


def test_spec_accepts_named_arg_handles_none_spec() -> None:
    assert _spec_accepts_named_arg(None, "anything") is False


# ---------------------------------------------------------------------------
# `_literal_values_for_named_arg` — TypeInfo walk
# ---------------------------------------------------------------------------


def test_literal_values_for_named_arg_extracts_literals() -> None:
    from typing import Literal as _Literal

    nested = [SimpleNamespace(name=f"'{v}'") for v in ("DEBUG", "INFO")]
    spec = SimpleNamespace(
        types={"level": SimpleNamespace(type=_Literal, nested=nested, is_union=False)},
    )
    assert _literal_values_for_named_arg(spec, "level") == ["DEBUG", "INFO"]


def test_literal_values_for_named_arg_handles_union_of_literal() -> None:
    """`level: Literal['A'] | None` shows up as union — walk it."""
    from typing import Literal as _Literal

    literal_branch = SimpleNamespace(
        type=_Literal,
        nested=[SimpleNamespace(name="'A'")],
        is_union=False,
    )
    none_branch = SimpleNamespace(type=type(None), nested=None, is_union=False)
    union_ti = SimpleNamespace(type=None, nested=[literal_branch, none_branch], is_union=True)
    spec = SimpleNamespace(types={"x": union_ti})
    assert _literal_values_for_named_arg(spec, "x") == ["A"]


def test_literal_values_for_named_arg_arg_not_in_types() -> None:
    spec = SimpleNamespace(types={})
    assert _literal_values_for_named_arg(spec, "level") == []


def test_literal_values_for_named_arg_none_spec() -> None:
    assert _literal_values_for_named_arg(None, "level") == []


# ---------------------------------------------------------------------------
# `current_named_arg_in_cell` — read the `name=` from the active cell
# ---------------------------------------------------------------------------


def test_current_named_arg_in_cell_finds_name() -> None:
    assert current_named_arg_in_cell("Log    level=DEBUG", 18) == "level"


def test_current_named_arg_in_cell_empty_value_after_equals() -> None:
    assert current_named_arg_in_cell("Log    level=", 13) == "level"


def test_current_named_arg_in_cell_no_equals_returns_none() -> None:
    assert current_named_arg_in_cell("Log    hello", 12) is None


def test_current_named_arg_in_cell_first_cell_returns_none() -> None:
    assert current_named_arg_in_cell("Log", 3) is None


def test_current_named_arg_in_cell_walks_past_indent() -> None:
    """Continuation-line indent shouldn't trick the cell walk."""
    buf = "FOR    ${i}    IN RANGE    3\n    Log    level=DEBUG"
    assert current_named_arg_in_cell(buf, len(buf)) == "level"


# ---------------------------------------------------------------------------
# `spec_arg_position` — flat-list display index for highlighting
# ---------------------------------------------------------------------------


def test_spec_arg_position_first_positional() -> None:
    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("message", "level", "html"),
        var_positional=None,
        named_only=(),
        var_named=None,
    )
    assert spec_arg_position(spec, "message") == 0
    assert spec_arg_position(spec, "level") == 1
    assert spec_arg_position(spec, "html") == 2


def test_spec_arg_position_accounts_for_var_positional() -> None:
    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("a",),
        var_positional="rest",
        named_only=("flag",),
        var_named=None,
    )
    # Display order: a, *rest, flag.
    assert spec_arg_position(spec, "a") == 0
    assert spec_arg_position(spec, "rest") == 1
    assert spec_arg_position(spec, "flag") == 2


def test_spec_arg_position_unknown_with_var_named_falls_into_kwargs() -> None:
    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("a",),
        var_positional=None,
        named_only=(),
        var_named="kw",
    )
    # Unknown name → the **kw slot (index 1, after `a`).
    assert spec_arg_position(spec, "unknown") == 1


def test_spec_arg_position_unknown_without_kwargs_is_none() -> None:
    spec = SimpleNamespace(
        positional_only=(),
        positional_or_named=("a",),
        var_positional=None,
        named_only=(),
        var_named=None,
    )
    assert spec_arg_position(spec, "unknown") is None


def test_spec_arg_position_none_spec() -> None:
    assert spec_arg_position(None, "a") is None


# ---------------------------------------------------------------------------
# Phase 4: dot-command completion + frame/scope-aware variable completion
# ---------------------------------------------------------------------------


def test_command_prefix_detects_bare_dot_token() -> None:
    from robotcode.repl._pt.completion import command_prefix

    assert command_prefix(".co") == "co"
    assert command_prefix(".") == ""
    assert command_prefix("Log    x") is None
    assert command_prefix("${x") is None
    assert command_prefix(".step over") is None  # has an argument cell → not a bare token


def test_complete_commands_filters_sorts_and_labels() -> None:
    from robotcode.repl._pt.completion import complete_commands

    labels = [c.label for c in complete_commands("c", ["continue", "step", "catch"])]
    assert labels == [".catch", ".continue"]  # only c-prefixed, sorted, dot-prefixed


def test_candidates_for_uses_explicit_variables_scope() -> None:
    """Variable completion honours an explicit `variables` store (a paused
    frame's scope) instead of the global execution context."""
    from types import SimpleNamespace

    from robotcode.repl._pt.completion import candidates_for, tokenize

    store = SimpleNamespace(as_dict=lambda: {"${MY_FRAME_VAR}": "hi", "${OTHER}": 1})
    ctx = tokenize("${MY", 4)
    labels = candidates_for(ctx, variables=store)
    assert "${MY_FRAME_VAR}" in labels
    assert "${OTHER}" not in labels  # prefix-filtered
