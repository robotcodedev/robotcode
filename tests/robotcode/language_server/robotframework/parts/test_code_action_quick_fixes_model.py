"""Equivalence tests for the SemanticModel-based "Create Keyword" quick fix.

Verifies that
`RobotCodeActionQuickFixesProtocolPart._resolve_create_keyword_target_from_model`
returns the same `(text, lib_entry)` tuple as the legacy AST + ModelHelper
path for the keyword-not-found scenarios that drive the quick fix.

Equivalence is the key safety net here because there are no existing E2E
regression tests for `code_action_quick_fixes.py`.
"""

import ast as _ast
from typing import Any, Callable, List, Optional

import pytest
from pytest_mock import MockerFixture

from robotcode.core.lsp.types import Position
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.parts.code_action_quick_fixes import (
    RobotCodeActionQuickFixesProtocolPart,
    _format_create_keyword_args,
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
    # Match the analyzer's `KeywordFinder` lookup by exposing keyword names
    # in `library_doc.keywords` via __contains__ (used by some helpers).
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

        # Mirror `libraries` into `_resolved_imports.libraries` so the
        # analyzer's own namespace dict (`analyzer._namespaces`, built
        # from `_resolved_imports.libraries.values()` in `analyzer.run`)
        # contains the same entries as `namespace.namespaces`. Without
        # this, the legacy path (which reads `namespace.namespaces`) and
        # the model path (which reads what the analyzer split) diverge in
        # tests even though they agree in production.
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
        namespace.finder = finder
        namespace.finder.find_keyword.side_effect = lambda name, raise_keyword_error=False, handle_bdd_style=True: (
            resolve(name)
        )
        return namespace, ast_model

    return factory


@pytest.fixture
def quick_fix_part_factory(
    mocker: MockerFixture,
) -> Callable[..., RobotCodeActionQuickFixesProtocolPart]:
    """Factory: build a stub protocol part bypassing LSP setup. Reads the
    namespace + AST off `__test_namespace__` / `__test_ast__` on the
    document, mirroring the other model-equivalence test files."""

    class _StubPart(RobotCodeActionQuickFixesProtocolPart):
        def __init__(self) -> None:
            self._parent_mock = mocker.MagicMock()
            self._parent_mock.documents_cache.get_namespace.side_effect = lambda doc: doc.__test_namespace__
            self._parent_mock.documents_cache.get_model.side_effect = lambda doc, *args, **kwargs: doc.__test_ast__

        @property
        def parent(self) -> Any:
            return self._parent_mock

    def factory() -> RobotCodeActionQuickFixesProtocolPart:
        return _StubPart()

    return factory


def _attach_to_document(document: TextDocument, namespace: Any, ast_model: _ast.AST) -> None:
    object.__setattr__(document, "__test_namespace__", namespace)
    object.__setattr__(document, "__test_ast__", ast_model)


# --------------------------------------------------------------------------
# Pure-function tests for `_format_create_keyword_args`.
# --------------------------------------------------------------------------


class TestFormatCreateKeywordArgs:
    def test_positional_args_become_arg_n_placeholders(self) -> None:
        assert _format_create_keyword_args(["alice", "bob"]) == ["${arg1}", "${arg2}"]

    def test_named_arg_uses_the_name(self) -> None:
        assert _format_create_keyword_args(["msg=hello", "level=INFO"]) == ["${msg}", "${level}"]

    def test_mixed_positional_and_named(self) -> None:
        assert _format_create_keyword_args(["alice", "level=INFO", "extra"]) == [
            "${arg1}",
            "${level}",
            "${arg3}",
        ]

    def test_named_with_variable_in_name_falls_back_to_arg_n(self) -> None:
        # `${var}=value` — name contains a variable → argN placeholder
        assert _format_create_keyword_args(["${var}=value"]) == ["${arg1}"]

    def test_empty_input_returns_empty(self) -> None:
        assert _format_create_keyword_args([]) == []


# --------------------------------------------------------------------------
# Equivalence: `_resolve_create_keyword_target` legacy vs model paths.
# --------------------------------------------------------------------------


_RESOLVE_CASES: list[tuple[str, str, dict[str, KeywordDoc], tuple[int, int]]] = [
    (
        "unknown_keyword_in_test_case",
        "*** Test Cases ***\nT\n    Unknown Keyword    arg\n",
        {},
        (2, 4),
    ),
    (
        "unknown_keyword_with_namespace_prefix_unresolved_lib",
        "*** Test Cases ***\nT\n    UnknownLib.Unknown Keyword\n",
        {},
        (2, 4),
    ),
    (
        # Known namespace, unknown keyword — both paths must strip the
        # `BuiltIn.` prefix and surface just the bare `Unknown Keyword`.
        # The fixture mirrors `analyzer._resolved_imports.libraries` to
        # `namespace.namespaces` so the analyzer's namespace splitter
        # sees the same set of known libraries as the legacy path does.
        "unknown_keyword_with_namespace_prefix_to_known_lib",
        "*** Test Cases ***\nT\n    BuiltIn.Unknown Keyword\n",
        {},
        (2, 4),
    ),
    (
        "unknown_keyword_in_setup",
        "*** Test Cases ***\nT\n    [Setup]    Unknown Setup Keyword\n",
        {},
        (2, 15),
    ),
    (
        "unknown_keyword_in_teardown",
        "*** Test Cases ***\nT\n    Pass\n    [Teardown]    Unknown Teardown Keyword\n",
        {"Pass": _kw("Pass")},
        (3, 18),
    ),
    (
        "unknown_keyword_in_keyword_definition",
        "*** Keywords ***\nMy Wrapper\n    Unknown Inner Keyword\n",
        {},
        (2, 4),
    ),
]


@pytest.mark.parametrize(
    ("name", "text", "kw_map", "position"),
    _RESOLVE_CASES,
    ids=[c[0] for c in _RESOLVE_CASES],
)
def test_resolve_create_keyword_target_matches(
    name: str,
    text: str,
    kw_map: dict[str, KeywordDoc],
    position: tuple[int, int],
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    quick_fix_part_factory: Callable[..., RobotCodeActionQuickFixesProtocolPart],
) -> None:
    """Both paths should return the same `(text, lib_entry)` tuple — even
    when `lib_entry` is a different *instance* (legacy walks
    `namespace.namespaces`, model reads `stmt.lib_entry`), the resolved
    name should match."""
    libraries: dict[str, Any] = {}
    # Make BuiltIn known to the namespace so the namespace-prefix case
    # finds a lib_entry.
    libraries[BUILTIN_LIBRARY_NAME] = _make_library_entry(mocker, BUILTIN_LIBRARY_NAME, list(kw_map.values()))

    namespace, ast_model = analyzer_namespace_factory(text, kw_map, libraries=libraries)
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = quick_fix_part_factory()
    pos = Position(line=position[0], character=position[1])

    legacy = part._resolve_create_keyword_target_legacy(document, pos, namespace)
    model = part._resolve_create_keyword_target_from_model(pos, namespace.semantic_model)

    assert legacy is not None, f"{name}: legacy returned None unexpectedly"
    assert model is not None, f"{name}: model returned None unexpectedly"

    legacy_text, legacy_lib = legacy
    model_text, model_lib = model

    assert legacy_text == model_text, f"{name}: text mismatch — legacy={legacy_text!r} model={model_text!r}"
    # `lib_entry` may be the same MagicMock instance in our setup, so
    # identity comparison works; both should be either None or the same
    # mock entry.
    assert (legacy_lib is None) == (model_lib is None), (
        f"{name}: lib_entry None-ness mismatch — legacy={legacy_lib!r} model={model_lib!r}"
    )
    if legacy_lib is not None and model_lib is not None:
        assert legacy_lib.name == model_lib.name, (
            f"{name}: lib_entry name mismatch — legacy={legacy_lib.name!r} model={model_lib.name!r}"
        )


# --------------------------------------------------------------------------
# Equivalence: argument collection legacy vs model.
# --------------------------------------------------------------------------


_ARGS_CASES: list[tuple[str, str, tuple[int, int], list[str]]] = [
    (
        "no_args",
        "*** Test Cases ***\nT\n    Unknown Keyword\n",
        (2, 4),
        [],
    ),
    (
        "two_positional_args",
        "*** Test Cases ***\nT\n    Unknown Keyword    foo    bar\n",
        (2, 4),
        ["${arg1}", "${arg2}"],
    ),
    (
        "named_args",
        "*** Test Cases ***\nT\n    Unknown Keyword    msg=hello    level=INFO\n",
        (2, 4),
        ["${msg}", "${level}"],
    ),
    (
        "mixed_args",
        "*** Test Cases ***\nT\n    Unknown Keyword    alice    level=INFO    extra\n",
        (2, 4),
        ["${arg1}", "${level}", "${arg3}"],
    ),
    (
        "named_with_variable_in_name",
        # `${name}=value` — name contains variable → argN placeholder
        "*** Test Cases ***\nT\n    Unknown Keyword    ${name}=value\n",
        (2, 4),
        ["${arg1}"],
    ),
]


@pytest.mark.parametrize(
    ("scenario", "text", "position", "expected"),
    _ARGS_CASES,
    ids=[c[0] for c in _ARGS_CASES],
)
def test_collect_create_keyword_arguments_matches(
    scenario: str,
    text: str,
    position: tuple[int, int],
    expected: list[str],
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    quick_fix_part_factory: Callable[..., RobotCodeActionQuickFixesProtocolPart],
) -> None:
    """`_collect_create_keyword_arguments` is dispatched by `semantic_model`
    presence; both paths must produce the same placeholder list for the
    same input call."""
    namespace, ast_model = analyzer_namespace_factory(text, {})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = quick_fix_part_factory()
    pos = Position(line=position[0], character=position[1])

    # Model path
    args_model = part._collect_create_keyword_arguments(document, pos, namespace)
    # Legacy path: temporarily clear semantic_model
    namespace.semantic_model = None
    args_legacy = part._collect_create_keyword_arguments(document, pos, namespace)

    assert args_model == expected, f"{scenario} model: expected {expected}, got {args_model}"
    assert args_legacy == expected, f"{scenario} legacy: expected {expected}, got {args_legacy}"


# --------------------------------------------------------------------------
# Negative cases — both paths return None when there's nothing to create.
# --------------------------------------------------------------------------


def test_resolve_target_returns_none_outside_keyword_call(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    quick_fix_part_factory: Callable[..., RobotCodeActionQuickFixesProtocolPart],
) -> None:
    """Cursor on a Documentation setting (not a keyword call) — both paths
    return None."""
    text = "*** Settings ***\nDocumentation    blah blah\n*** Test Cases ***\nT\n    Pass\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Pass": _kw("Pass")})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = quick_fix_part_factory()
    pos = Position(line=1, character=4)

    assert part._resolve_create_keyword_target_legacy(document, pos, namespace) is None
    assert part._resolve_create_keyword_target_from_model(pos, namespace.semantic_model) is None


def test_resolve_target_returns_none_in_keyword_definition_header(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    quick_fix_part_factory: Callable[..., RobotCodeActionQuickFixesProtocolPart],
) -> None:
    """Cursor on a keyword definition's name (a `KeywordName` AST node, not
    a `KeywordCall`) — both paths return None because there's no missing
    keyword to create here."""
    text = "*** Keywords ***\nMy Wrapper\n    Pass\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Pass": _kw("Pass")})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = quick_fix_part_factory()
    pos = Position(line=1, character=4)

    legacy = part._resolve_create_keyword_target_legacy(document, pos, namespace)
    model = part._resolve_create_keyword_target_from_model(pos, namespace.semantic_model)
    assert legacy is None
    assert model is None
