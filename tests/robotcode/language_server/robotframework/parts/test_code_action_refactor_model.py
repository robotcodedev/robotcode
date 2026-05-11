"""Equivalence tests for the SemanticModel-based "Assign keyword result
to variable" refactor code action.

Verifies that
`RobotCodeActionRefactorProtocolPart._assign_result_insert_position_from_model`
returns the same insert Position as the legacy AST path for the cases
that drive the refactor — including BDD-prefixed and namespace-prefixed
keyword calls where the legacy path takes the start of the full RF
KEYWORD token (which spans `Given My KW` / `Lib.My KW`) and the model
path needs to take the leftmost SemanticToken in the keyword reference
span.

Equivalence is the safety net here because there are no existing E2E
regression tests for `code_action_refactor.py`.
"""

import ast as _ast
from typing import Any, Callable, List, Optional

import pytest
from pytest_mock import MockerFixture

from robotcode.core.lsp.types import Position
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.parts.code_action_refactor import (
    RobotCodeActionRefactorProtocolPart,
)
from robotcode.robot.diagnostics.entities import LibraryEntry
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
    spec = RobotArgumentSpec(
        name=name,
        type="Keyword",
        positional_only=[],
        positional_or_named=[a.name for a in args if a.kind is KeywordArgumentKind.POSITIONAL_OR_NAMED],
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


def _make_library_entry(
    mocker: MockerFixture,
    name: str,
    kw_docs: List[KeywordDoc],
    *,
    libtype: str = "LIBRARY",
    alias: Optional[str] = None,
) -> Any:
    entry = mocker.MagicMock(spec=LibraryEntry)
    entry.name = name
    entry.alias = alias
    entry.import_name = name
    entry.args = ()
    entry.library_doc = mocker.MagicMock()
    entry.library_doc.name = name
    entry.library_doc.type = libtype
    entry.library_doc.source = None
    entry.library_doc.errors = []
    entry.library_doc.inits = []
    kw_dict = {kw.name: kw for kw in kw_docs}
    entry.library_doc.keywords = mocker.MagicMock()
    entry.library_doc.keywords.keywords = kw_docs
    entry.library_doc.keywords.__contains__ = lambda self, item: item in kw_dict
    return entry


# --------------------------------------------------------------------------
# Fixtures.
# --------------------------------------------------------------------------


@pytest.fixture
def analyzer_namespace_factory(
    mocker: MockerFixture,
) -> Callable[..., tuple[Any, _ast.AST]]:
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

        if libraries is None:
            libraries = {}
            per_lib: dict[str, list[KeywordDoc]] = {}
            for kw in kw_map.values():
                per_lib.setdefault(kw.libname or BUILTIN_LIBRARY_NAME, []).append(kw)
            for lib_name, kws in per_lib.items():
                libraries[lib_name] = _make_library_entry(mocker, lib_name, kws)

        # Mirror libraries into _resolved_imports so analyzer's namespace
        # split sees the same set as namespace.namespaces (production parity).
        analyzer._resolved_imports = ResolvedImports(libraries=dict(libraries))

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
        namespace.find_variable.return_value = None  # no variable conflicts in tests
        namespace.finder = finder
        namespace.finder.find_keyword.side_effect = lambda name, raise_keyword_error=False, handle_bdd_style=True: (
            resolve(name)
        )
        return namespace, ast_model

    return factory


@pytest.fixture
def refactor_part_factory(
    mocker: MockerFixture,
) -> Callable[..., RobotCodeActionRefactorProtocolPart]:
    """Factory: build a stub protocol part bypassing LSP setup."""

    class _StubPart(RobotCodeActionRefactorProtocolPart):
        def __init__(self) -> None:
            self._parent_mock = mocker.MagicMock()
            self._parent_mock.documents_cache.get_namespace.side_effect = lambda doc: doc.__test_namespace__
            self._parent_mock.documents_cache.get_model.side_effect = lambda doc, *args, **kwargs: doc.__test_ast__

        @property
        def parent(self) -> Any:
            return self._parent_mock

    def factory() -> RobotCodeActionRefactorProtocolPart:
        return _StubPart()

    return factory


def _attach_to_document(document: TextDocument, namespace: Any, ast_model: _ast.AST) -> None:
    object.__setattr__(document, "__test_namespace__", namespace)
    object.__setattr__(document, "__test_ast__", ast_model)


# --------------------------------------------------------------------------
# Equivalence: legacy vs model paths return the same insert Position.
# --------------------------------------------------------------------------


_CASES: list[tuple[str, str, dict[str, KeywordDoc], tuple[int, int], Optional[tuple[int, int]]]] = [
    (
        # Plain keyword call, cursor on the keyword name → insert at the
        # start of "Log".
        "plain_keyword_call_cursor_on_name",
        "*** Test Cases ***\nT\n    Log    msg\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        (2, 5),
        (2, 4),
    ),
    (
        # Cursor on the namespace prefix part of `BuiltIn.Log` — both paths
        # must accept it (legacy uses the full KW token range) and insert
        # at the start of "BuiltIn".
        "namespace_prefixed_cursor_on_namespace",
        "*** Test Cases ***\nT\n    BuiltIn.Log    msg\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        (2, 6),
        (2, 4),
    ),
    (
        # Cursor on the keyword part after the namespace dot.
        "namespace_prefixed_cursor_on_keyword_after_dot",
        "*** Test Cases ***\nT\n    BuiltIn.Log    msg\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        (2, 13),
        (2, 4),
    ),
    (
        # Cursor on the dot itself — legacy includes it (cursor in the
        # full KW token range), model includes it (covered by SEPARATOR
        # SemanticToken).
        "namespace_prefixed_cursor_on_dot",
        "*** Test Cases ***\nT\n    BuiltIn.Log    msg\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        (2, 11),
        (2, 4),
    ),
    (
        # Already has an assignment → both paths return None.
        "already_has_assignment_returns_none",
        "*** Test Cases ***\nT\n    ${r}=    Log    msg\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        (2, 13),
        None,
    ),
    (
        # Cursor on an argument, not on the keyword name → both return None.
        "cursor_on_argument_returns_none",
        "*** Test Cases ***\nT\n    Log    msg\n",
        {"Log": _kw("Log", args=[_arg("message")])},
        (2, 12),
        None,
    ),
    (
        # Cursor on a Setup fixture is NOT a KeywordCall AST node, legacy
        # filters via `isinstance(node, KeywordCall)` → None. Model uses
        # the same kind filter (only KEYWORD_CALL kind) → None.
        "setup_fixture_returns_none",
        "*** Test Cases ***\nT\n    [Setup]    Log    msg\n    Pass\n",
        {"Log": _kw("Log", args=[_arg("message")]), "Pass": _kw("Pass")},
        (2, 16),
        None,
    ),
]


@pytest.mark.parametrize(
    ("name", "text", "kw_map", "position", "expected_pos"),
    _CASES,
    ids=[c[0] for c in _CASES],
)
def test_assign_result_insert_position_matches(
    name: str,
    text: str,
    kw_map: dict[str, KeywordDoc],
    position: tuple[int, int],
    expected_pos: Optional[tuple[int, int]],
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    refactor_part_factory: Callable[..., RobotCodeActionRefactorProtocolPart],
) -> None:
    namespace, ast_model = analyzer_namespace_factory(text, kw_map)
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = refactor_part_factory()
    pos = Position(line=position[0], character=position[1])

    legacy = part._assign_result_insert_position_legacy(document, pos)
    model = part._assign_result_insert_position_from_model(pos, namespace.semantic_model)

    assert legacy == model, f"{name}: legacy != model — legacy={legacy}, model={model}"
    if expected_pos is None:
        assert legacy is None
    else:
        assert legacy == Position(line=expected_pos[0], character=expected_pos[1])


# --------------------------------------------------------------------------
# Dispatcher: `_assign_result_insert_position` picks the right path
# depending on `namespace.semantic_model` presence.
# --------------------------------------------------------------------------


def test_dispatcher_uses_model_when_semantic_model_present(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    refactor_part_factory: Callable[..., RobotCodeActionRefactorProtocolPart],
) -> None:
    text = "*** Test Cases ***\nT\n    Log    msg\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = refactor_part_factory()
    spy_model = mocker.spy(part, "_assign_result_insert_position_from_model")
    spy_legacy = mocker.spy(part, "_assign_result_insert_position_legacy")

    part._assign_result_insert_position(document, Position(line=2, character=5), namespace)

    assert spy_model.called
    assert not spy_legacy.called


def test_dispatcher_falls_back_to_legacy_when_no_semantic_model(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    refactor_part_factory: Callable[..., RobotCodeActionRefactorProtocolPart],
) -> None:
    text = "*** Test Cases ***\nT\n    Log    msg\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Log": _kw("Log", args=[_arg("message")])})
    namespace.semantic_model = None
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = refactor_part_factory()
    spy_model = mocker.spy(part, "_assign_result_insert_position_from_model")
    spy_legacy = mocker.spy(part, "_assign_result_insert_position_legacy")

    part._assign_result_insert_position(document, Position(line=2, character=5), namespace)

    assert not spy_model.called
    assert spy_legacy.called
