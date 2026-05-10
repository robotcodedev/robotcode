"""Equivalence tests for the SemanticModel-based code-action-documentation path.

Verifies that `RobotCodeActionDocumentationProtocolPart._collect_from_model(...)`
produces the same `[Open Documentation]` actions as the legacy
`_collect_legacy(...)` path across the three relevant statement kinds:
- Library / Resource imports
- KeywordCall / Fixture / Template / TestTemplate
- KeywordName (definition headers)

Style mirrors `test_signature_help_model.py` — analyzer + namespace
factory, stub protocol part, parametrised equivalence cases.
"""

import ast as _ast
from typing import Any, Callable, List, Optional

import pytest
from pytest_mock import MockerFixture

from robotcode.core.lsp.types import (
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    CodeActionTriggerKind,
    Command,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.parts.code_action_documentation import (
    RobotCodeActionDocumentationProtocolPart,
)
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.library_doc import (
    BUILTIN_LIBRARY_NAME,
    ArgumentInfo,
    KeywordArgumentKind,
    KeywordDoc,
)
from robotcode.robot.diagnostics.library_doc import (
    ArgumentSpec as RobotArgumentSpec,
)
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import (
    SemanticAnalyzer,
    _get_builtin_variables,
)
from robotcode.robot.diagnostics.variable_scope import VariableScope
from tests.robotcode.conftest import make_resource_doc, parse_robot

# --------------------------------------------------------------------------
# Plain-data builders.
# --------------------------------------------------------------------------


def _arg(
    name: str,
    kind: KeywordArgumentKind = KeywordArgumentKind.POSITIONAL_OR_NAMED,
) -> ArgumentInfo:
    return ArgumentInfo(name=name, str_repr=name, kind=kind, required=False, default_value=None)


def _kw(
    name: str,
    *,
    args: Optional[List[ArgumentInfo]] = None,
    libname: str = BUILTIN_LIBRARY_NAME,
    libtype: str = "LIBRARY",
) -> KeywordDoc:
    args = args or []
    positional_or_named = [a.name for a in args if a.kind is KeywordArgumentKind.POSITIONAL_OR_NAMED]
    spec = RobotArgumentSpec(
        name=name,
        type="Keyword",
        positional_only=[],
        positional_or_named=positional_or_named,
        var_positional=None,
        named_only=[],
        var_named=None,
        defaults={},
        embedded=[],
        types=None,
        return_type=None,
    )
    return KeywordDoc(
        line_no=-1,
        col_offset=-1,
        end_line_no=-1,
        end_col_offset=-1,
        source=None,
        name=name,
        libname=libname,
        libtype=libtype,
        arguments=args,
        arguments_spec=spec,
    )


def _make_text_document(text: str, source: str = "/test.robot") -> TextDocument:
    return TextDocument(
        document_uri=f"file://{source}",
        language_id="robotframework",
        version=0,
        text=text,
    )


# --------------------------------------------------------------------------
# Mock-builder fixtures.
# --------------------------------------------------------------------------


def _make_library_entry(
    mocker: MockerFixture,
    name: str,
    kw_docs: List[KeywordDoc],
    alias: Optional[str] = None,
) -> Any:
    entry = mocker.MagicMock()
    entry.name = name
    entry.alias = alias
    entry.import_name = name
    entry.args = ()
    entry.library_doc = mocker.MagicMock()
    entry.library_doc.name = name
    entry.library_doc.keywords = mocker.MagicMock()
    entry.library_doc.keywords.keywords = kw_docs
    entry.library_doc.errors = []
    entry.library_doc.inits = []
    # Tie kw_docs back to the libdoc so `kw_doc.parent == lib.library_doc`
    # works for `_build_keyword_action`'s lookup.
    for kw in kw_docs:
        kw.parent = entry.library_doc
    return entry


@pytest.fixture
def analyzer_namespace_factory(
    mocker: MockerFixture,
) -> Callable[..., tuple[Any, _ast.AST]]:
    """Factory: parse Robot text, run the SemanticAnalyzer, and wrap a fake
    Namespace around the result so both legacy and model paths can be invoked
    against the same inputs."""

    def factory(
        text: str,
        kw_map: dict[str, KeywordDoc],
        libraries: Optional[dict[str, Any]] = None,
        source: str = "/test.robot",
    ) -> tuple[Any, _ast.AST]:
        ast_model = parse_robot(text)
        analyzer = SemanticAnalyzer(ast_model, source, f"file://{source}")
        analyzer._library_doc = make_resource_doc(source)
        analyzer._variable_scope = VariableScope(
            command_line=[],
            own=[],
            builtin=_get_builtin_variables(),
        )
        analyzer._resolved_imports = ResolvedImports()

        if libraries is None:
            libraries = {}
            per_lib: dict[str, list[KeywordDoc]] = {}
            for kw in kw_map.values():
                per_lib.setdefault(kw.libname or BUILTIN_LIBRARY_NAME, []).append(kw)
            for lib_name, kws in per_lib.items():
                libraries[lib_name] = _make_library_entry(mocker, lib_name, kws)

        libname_to_kws: dict[str, set[str]] = {}
        for lib_key, lib_entry in libraries.items():
            kw_names = {kw.name for kw in lib_entry.library_doc.keywords.keywords}
            libname_to_kws[lib_key] = kw_names

        def resolve(name: str) -> Optional[KeywordDoc]:
            if "." in name:
                ns_name, kw_name = name.split(".", 1)
                if ns_name not in libname_to_kws or kw_name not in libname_to_kws[ns_name]:
                    return None
                return kw_map.get(kw_name)
            return kw_map.get(name)

        finder = mocker.create_autospec(KeywordFinder, instance=True)
        finder.find_keyword.side_effect = lambda name, raise_keyword_error=True: resolve(name)
        finder.result_bdd_prefix = None
        finder.multiple_keywords_result = None
        finder.diagnostics = []

        result = analyzer.run(finder)

        namespace = mocker.MagicMock()
        namespace.semantic_model = result.semantic_model
        namespace.libraries = libraries
        namespace.resources = {}
        namespace.namespaces = {n: [e] for n, e in libraries.items()}
        namespace.languages = None
        namespace.library_doc = analyzer._library_doc
        namespace.find_keyword.side_effect = lambda name, raise_keyword_error=False, handle_bdd_style=True: resolve(
            name
        )
        namespace.finder = finder
        namespace.finder.find_keyword.side_effect = lambda name, raise_keyword_error=False, handle_bdd_style=True: (
            resolve(name)
        )
        return namespace, ast_model

    return factory


@pytest.fixture
def code_action_part_factory(
    mocker: MockerFixture,
) -> Callable[..., RobotCodeActionDocumentationProtocolPart]:
    """Factory: build a `RobotCodeActionDocumentationProtocolPart` stub
    bypassing LSP setup. Reads `__test_namespace__` / `__test_ast__` off the
    document the same way the inlay-hint and signature-help test parts do.
    """

    class _StubPart(RobotCodeActionDocumentationProtocolPart):
        def __init__(self) -> None:
            self._parent_mock = mocker.MagicMock()
            self._parent_mock.documents_cache.get_namespace.side_effect = lambda doc: doc.__test_namespace__
            self._parent_mock.documents_cache.get_model.side_effect = lambda doc, *args, **kwargs: doc.__test_ast__
            # `build_url` reads `parent.http_server.port` and
            # `parent.workspace.get_workspace_folder(...)`. Wire both
            # to fixed values so URLs are stable across runs.
            self._parent_mock.http_server.port = 12345
            self._parent_mock.workspace.get_workspace_folder.return_value = None

        @property
        def parent(self) -> Any:
            return self._parent_mock

    def factory() -> RobotCodeActionDocumentationProtocolPart:
        return _StubPart()

    return factory


def _attach_to_document(document: TextDocument, namespace: Any, ast_model: _ast.AST) -> None:
    object.__setattr__(document, "__test_namespace__", namespace)
    object.__setattr__(document, "__test_ast__", ast_model)


# --------------------------------------------------------------------------
# Equivalence helper.
# --------------------------------------------------------------------------


def _normalize(actions: Optional[List[Any]]) -> Any:
    if actions is None:
        return None
    out = []
    for a in actions:
        if isinstance(a, CodeAction):
            out.append(
                {
                    "title": a.title,
                    "kind": a.kind,
                    "command_name": a.command.command if a.command else None,
                    "command_args": list(a.command.arguments) if a.command and a.command.arguments else None,
                }
            )
        elif isinstance(a, Command):
            out.append({"command_name": a.command, "command_args": list(a.arguments) if a.arguments else None})
    return out


def _ctx() -> CodeActionContext:
    return CodeActionContext(
        diagnostics=[],
        only=[CodeActionKind.SOURCE.value],
        trigger_kind=CodeActionTriggerKind.INVOKED,
    )


# --------------------------------------------------------------------------
# Cases — covers all three branches plus negative positions.
# --------------------------------------------------------------------------


_CASES: list[tuple[str, str, dict[str, KeywordDoc], list[tuple[int, int]]]] = [
    (
        "library_import_cursor_on_name",
        "*** Settings ***\nLibrary    Collections\n*** Test Cases ***\nT\n    Log    hi\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (1, 12),  # cursor on "Collections"
            (1, 17),  # cursor inside "Collections"
        ],
    ),
    (
        "library_import_cursor_off_name_returns_none",
        "*** Settings ***\nLibrary    Collections\n*** Test Cases ***\nT\n    Log    hi\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (1, 0),  # cursor on "Library" word — both paths return None
        ],
    ),
    (
        "keyword_call_cursor_on_name",
        "*** Test Cases ***\nT\n    Log    hi\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (2, 4),  # cursor on "L" of Log
            (2, 5),  # cursor inside Log
            (2, 7),  # cursor at end of Log
        ],
    ),
    (
        "keyword_call_cursor_on_arg_returns_none",
        "*** Test Cases ***\nT\n    Log    hello\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (2, 12),  # cursor on "hello" — not on the keyword name
        ],
    ),
    (
        "keyword_call_with_namespace_prefix",
        "*** Test Cases ***\nT\n    BuiltIn.Log    hi\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (2, 4),  # cursor on "BuiltIn"
            (2, 12),  # cursor on Log part of BuiltIn.Log
        ],
    ),
    (
        "setup_fixture_cursor_on_name",
        "*** Test Cases ***\nT\n    [Setup]    Log    hi\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (2, 15),  # cursor on Log inside [Setup]
        ],
    ),
    (
        "teardown_fixture_cursor_on_name",
        "*** Test Cases ***\nT\n    Log    msg\n    [Teardown]    Log    bye\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (3, 18),  # cursor on Log inside [Teardown]
        ],
    ),
    (
        "test_template_cursor_on_name",
        "*** Settings ***\nTest Template    Log\n*** Test Cases ***\nT\n    msg\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (1, 17),  # cursor on Log inside Test Template
        ],
    ),
    (
        "template_cursor_on_name",
        "*** Test Cases ***\nT\n    [Template]    Log\n    msg\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (2, 18),  # cursor on Log inside [Template]
        ],
    ),
    (
        "keyword_definition_name_cursor_on",
        "*** Keywords ***\nMy Keyword\n    [Arguments]    ${x}\n    Log    ${x}\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            (1, 0),  # cursor at start of "My Keyword"
            (1, 5),  # cursor inside "My Keyword"
        ],
    ),
    (
        "selection_returns_none_for_keyword_call",
        "*** Test Cases ***\nT\n    Log    hi\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        [
            # Selection (start != end) — the legacy / model paths both return
            # None for KeywordCall but only inside the kw-call branch. We
            # exercise this by passing a non-empty selection in the test
            # function below; the position list still matters for placing it.
            (2, 4),
        ],
    ),
]


@pytest.mark.parametrize(
    ("name", "text", "kw_map", "positions"),
    _CASES,
    ids=[c[0] for c in _CASES],
)
def test_legacy_and_model_paths_match(
    name: str,
    text: str,
    kw_map: dict[str, KeywordDoc],
    positions: list[tuple[int, int]],
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    namespace, ast_model = analyzer_namespace_factory(text, kw_map)
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()

    for line, char in positions:
        rng = Range(start=Position(line=line, character=char), end=Position(line=line, character=char))

        legacy = part._collect_legacy(document, rng, _ctx(), namespace)
        model = part._collect_from_model(document, rng, _ctx(), namespace, namespace.semantic_model)

        assert _normalize(legacy) == _normalize(model), (
            f"{name} @ ({line},{char}): legacy != model\n  legacy={_normalize(legacy)}\n  model ={_normalize(model)}"
        )


def test_keyword_call_with_selection_returns_none_in_both_paths(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    """Both paths return None when the user has a non-empty selection on a
    KeywordCall — code action is offered only for a single-point cursor."""
    text = "*** Test Cases ***\nT\n    Log    hi\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()
    rng = Range(start=Position(line=2, character=4), end=Position(line=2, character=7))  # selecting "Log"

    legacy = part._collect_legacy(document, rng, _ctx(), namespace)
    model = part._collect_from_model(document, rng, _ctx(), namespace, namespace.semantic_model)
    assert legacy is None
    assert model is None


# --------------------------------------------------------------------------
# CodeActionContext.only variations: the three branches react differently.
# Library/Resource: gated at branch entry. KeywordCall: gated before output.
# KeywordName: NOT gated at all (always returns the action). The model
# path must mirror that asymmetry exactly.
# --------------------------------------------------------------------------


@pytest.fixture
def keyword_call_text_and_namespace(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
) -> tuple[str, Any, _ast.AST]:
    text = "*** Test Cases ***\nT\n    Log    hi\n"
    ns, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    return text, ns, ast_model


def _ctx_with(only: Optional[List[str]]) -> CodeActionContext:
    return CodeActionContext(
        diagnostics=[],
        only=only,
        trigger_kind=CodeActionTriggerKind.INVOKED,
    )


@pytest.mark.parametrize(
    ("scenario", "text_and_position", "context_only"),
    [
        # Library import: SOURCE absent → both paths return None.
        (
            "library_import_context_only_none",
            ("*** Settings ***\nLibrary    Collections\n", (1, 12)),
            None,
        ),
        (
            "library_import_context_only_refactor",
            ("*** Settings ***\nLibrary    Collections\n", (1, 12)),
            [CodeActionKind.REFACTOR.value],
        ),
        # KeywordCall: SOURCE absent → both paths return None.
        (
            "keyword_call_context_only_none",
            ("*** Test Cases ***\nT\n    Log    hi\n", (2, 5)),
            None,
        ),
        (
            "keyword_call_context_only_refactor",
            ("*** Test Cases ***\nT\n    Log    hi\n", (2, 5)),
            [CodeActionKind.REFACTOR.value],
        ),
        # KeywordName: NO context.only check in legacy → both paths return
        # the action regardless.
        (
            "keyword_definition_context_only_none",
            ("*** Keywords ***\nMy Keyword\n    Log    hi\n", (1, 3)),
            None,
        ),
        (
            "keyword_definition_context_only_refactor",
            ("*** Keywords ***\nMy Keyword\n    Log    hi\n", (1, 3)),
            [CodeActionKind.REFACTOR.value],
        ),
    ],
)
def test_context_only_gating_matches(
    scenario: str,
    text_and_position: tuple[str, tuple[int, int]],
    context_only: Optional[List[str]],
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    """The three legacy branches gate on `context.only` differently. The
    model path must reproduce each branch's gating exactly."""
    text, (line, char) = text_and_position
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()
    rng = Range(start=Position(line=line, character=char), end=Position(line=line, character=char))
    ctx = _ctx_with(context_only)

    legacy = part._collect_legacy(document, rng, ctx, namespace)
    model = part._collect_from_model(document, rng, ctx, namespace, namespace.semantic_model)

    assert _normalize(legacy) == _normalize(model), (
        f"{scenario}: legacy != model\n  legacy={_normalize(legacy)}\n  model ={_normalize(model)}"
    )


# --------------------------------------------------------------------------
# Statement types the legacy AST branch never matches: VariablesImport,
# unresolved keyword calls. Both paths must return None.
# --------------------------------------------------------------------------


def test_variables_import_returns_none_in_both_paths(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    """Legacy `_collect_legacy` only matches `LibraryImport` / `ResourceImport`
    — `VariablesImport` falls through. The model path must do the same."""
    text = "*** Settings ***\nVariables    vars.py\n*** Test Cases ***\nT\n    Log    hi\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()
    rng = Range(start=Position(line=1, character=14), end=Position(line=1, character=14))

    legacy = part._collect_legacy(document, rng, _ctx(), namespace)
    model = part._collect_from_model(document, rng, _ctx(), namespace, namespace.semantic_model)

    assert legacy is None
    assert model is None


def test_unresolved_keyword_call_returns_none_in_both_paths(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    """Cursor on an unknown keyword name — `find_keyword` returns None in
    legacy, `KeywordCallStatement.keyword_doc` is None in model. Both must
    return None (not crash, not produce a stale URL)."""
    text = "*** Test Cases ***\nT\n    Unknown Keyword    arg\n"
    namespace, ast_model = analyzer_namespace_factory(text, {})  # empty kw_map
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()
    rng = Range(start=Position(line=2, character=4), end=Position(line=2, character=4))

    legacy = part._collect_legacy(document, rng, _ctx(), namespace)
    model = part._collect_from_model(document, rng, _ctx(), namespace, namespace.semantic_model)

    assert legacy is None
    assert model is None


# --------------------------------------------------------------------------
# Library import edge cases (WITH NAME alias) and embedded-args keywords.
# Both appear in the E2E `code_action_show_documentation.robot` data; this
# section exercises them directly so unit-level diffs surface immediately.
# --------------------------------------------------------------------------


def test_library_import_with_name_alias_cursor_on_lib_name(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    text = "*** Settings ***\nLibrary    Collections    WITH NAME    Coll\n*** Test Cases ***\nT\n    Log    hi\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()
    # Cursor on "Collections" (the library name itself, not the alias).
    rng = Range(start=Position(line=1, character=14), end=Position(line=1, character=14))

    legacy = part._collect_legacy(document, rng, _ctx(), namespace)
    model = part._collect_from_model(document, rng, _ctx(), namespace, namespace.semantic_model)

    assert _normalize(legacy) == _normalize(model)


def test_keyword_definition_with_embedded_args_cursor_on_name(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    """Embedded-argument keywords — `add ${number:[0-9]+} coins` — render the
    name as a single KEYWORD_NAME token. The action must fire on any
    cursor inside that token range, including over the embedded variable
    syntax."""
    text = "*** Keywords ***\nadd ${number:[0-9]+} coins\n    Log    ${number}\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()

    for char in (0, 4, 12, 25):
        rng = Range(start=Position(line=1, character=char), end=Position(line=1, character=char))
        legacy = part._collect_legacy(document, rng, _ctx(), namespace)
        model = part._collect_from_model(document, rng, _ctx(), namespace, namespace.semantic_model)
        assert _normalize(legacy) == _normalize(model), (
            f"embedded-args keyword @ char={char}: legacy={_normalize(legacy)}, model={_normalize(model)}"
        )


def test_resource_import_cursor_on_name(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    """Resource imports go through the same import branch as Library
    imports (both paths produce the documentation action)."""
    text = "*** Settings ***\nResource    common.resource\n*** Test Cases ***\nT\n    Log    hi\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()
    rng = Range(
        start=Position(line=1, character=14),
        end=Position(line=1, character=14),
    )

    legacy = part._collect_legacy(document, rng, _ctx(), namespace)
    model = part._collect_from_model(document, rng, _ctx(), namespace, namespace.semantic_model)

    assert _normalize(legacy) == _normalize(model)


# --------------------------------------------------------------------------
# Dispatch tests
# --------------------------------------------------------------------------


def test_collect_dispatches_to_model_path_when_semantic_model_available(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    text = "*** Test Cases ***\nT\n    Log    hi\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()
    spy_model = mocker.spy(part, "_collect_from_model")
    spy_legacy = mocker.spy(part, "_collect_legacy")

    rng = Range(start=Position(line=2, character=4), end=Position(line=2, character=4))
    part.collect(part, document, rng, _ctx())

    assert spy_model.called
    assert not spy_legacy.called


def test_collect_dispatches_to_legacy_path_when_no_semantic_model(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    code_action_part_factory: Callable[..., RobotCodeActionDocumentationProtocolPart],
) -> None:
    text = "*** Test Cases ***\nT\n    Log    hi\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    namespace.semantic_model = None
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = code_action_part_factory()
    spy_model = mocker.spy(part, "_collect_from_model")
    spy_legacy = mocker.spy(part, "_collect_legacy")

    rng = Range(start=Position(line=2, character=4), end=Position(line=2, character=4))
    part.collect(part, document, rng, _ctx())

    assert not spy_model.called
    assert spy_legacy.called
