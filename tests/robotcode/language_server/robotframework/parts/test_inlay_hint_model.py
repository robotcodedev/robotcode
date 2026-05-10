"""Unit tests for the SemanticModel-based inlay hint path.

Tests that `_get_inlay_hint_from_semantic_tokens` (used by the
`semantic_model` branch in `RobotInlayHintProtocolPart.collect`) produces
the same parameter-name and namespace hints as the legacy AST-based
`_get_inlay_hint` path.

Style: idiomatic pytest — `mocker: MockerFixture` parameter for tests that
need mocks, `@pytest.fixture` for shared setup. Plain-data builders
(`_kw`, `_arg`, `_semantic_token`) stay as plain functions because they
construct real dataclass instances, not mocks.
"""

import ast as _ast
from typing import Any, Callable, List, Optional

import pytest
from pytest_mock import MockerFixture
from robot.parsing.lexer.tokens import Token

from robotcode.core.lsp.types import InlayHint, InlayHintKind, Position
from robotcode.core.lsp.types import Range as LspRange
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.configuration import InlayHintsConfig
from robotcode.language_server.robotframework.parts.inlay_hint import RobotInlayHintProtocolPart
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
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import SemanticAnalyzer, _get_builtin_variables
from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType, TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    ImportStatement,
    KeywordCallStatement,
    SemanticToken,
)
from robotcode.robot.diagnostics.variable_scope import VariableScope
from tests.robotcode.conftest import make_resource_doc, parse_robot

# --------------------------------------------------------------------------
# Plain-data builders (no mocks — used by every test).
# --------------------------------------------------------------------------


def _arg(name: str, kind: KeywordArgumentKind = KeywordArgumentKind.POSITIONAL_OR_NAMED) -> ArgumentInfo:
    return ArgumentInfo(name=name, str_repr=name, kind=kind, required=False, default_value=None)


def _kw(
    name: str,
    *,
    args: Optional[List[ArgumentInfo]] = None,
    libname: str = BUILTIN_LIBRARY_NAME,
    libtype: str = "LIBRARY",
) -> KeywordDoc:
    """Build a minimal KeywordDoc with a usable argument spec."""
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


def _config(parameter_names: bool = True, namespaces: bool = False) -> InlayHintsConfig:
    return InlayHintsConfig(parameter_names=parameter_names, namespaces=namespaces)


def _semantic_token(kind: TokenKind, value: str, line: int, col: int) -> SemanticToken:
    return SemanticToken(kind=kind, value=value, line=line, col_offset=col, length=len(value))


def _make_text_document(text: str, source: str = "/test.robot") -> TextDocument:
    return TextDocument(
        document_uri=str(Uri.from_path(source)),
        language_id="robotframework",
        version=0,
        text=text,
    )


def _normalize_hints(hints: Optional[List[InlayHint]]) -> List[tuple[Any, tuple[int, int], Optional[InlayHintKind]]]:
    if hints is None:
        return []
    return [(h.label, (h.position.line, h.position.character), h.kind) for h in hints]


# --------------------------------------------------------------------------
# Mock builders — take `mocker` as parameter (project convention; see
# tests/robotcode/robot/diagnostics/test_project_index.py).
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
    entry.library_doc = mocker.MagicMock()
    entry.library_doc.keywords = mocker.MagicMock()
    entry.library_doc.keywords.keywords = kw_docs
    return entry


def _make_simple_namespace_with_lib(
    mocker: MockerFixture,
    kw_doc: KeywordDoc,
    lib_name: str = "MyLib",
) -> Any:
    """Minimal Namespace mock for the pure-function helper tests."""
    ns = mocker.MagicMock()
    ns.libraries = {lib_name: _make_library_entry(mocker, lib_name, [kw_doc])}
    ns.resources = {}
    return ns


# --------------------------------------------------------------------------
# Fixtures.
# --------------------------------------------------------------------------


@pytest.fixture
def cfg() -> Callable[..., InlayHintsConfig]:
    """Factory: build an InlayHintsConfig with named arguments."""
    return _config


# Cross-product config axes for parametrized equivalence tests.
_CONFIG_AXES: list[tuple[str, bool, bool]] = [
    ("params_only", True, False),
    ("ns_only", False, True),
    ("both", True, True),
]


@pytest.fixture(
    params=_CONFIG_AXES,
    ids=[a[0] for a in _CONFIG_AXES],
)
def axis(request: pytest.FixtureRequest) -> tuple[str, bool, bool]:
    """One row of `_CONFIG_AXES`. Use this in tests that should run against
    every `(parameter_names, namespaces)` toggle combination."""
    return request.param  # type: ignore[no-any-return]


@pytest.fixture
def analyzer_namespace_factory(
    mocker: MockerFixture,
) -> Callable[..., tuple[Any, _ast.AST]]:
    """Factory: parse Robot text, run the SemanticAnalyzer, and wrap a fake
    Namespace around the result.

    The namespace is wired so that:
    - the analyzer's `KeywordFinder` resolves the supplied `kw_map` (with
      realistic `Lib.Keyword` namespace handling — unknown namespaces return
      None, like the real `KeywordFinder._get_explicit_keyword`)
    - the legacy inlay-hint path's `namespace.find_keyword` /
      `namespace.finder.find_keyword` use the same resolver
    - `namespace.libraries` is auto-built from `kw_map`'s libnames unless
      explicitly provided via `libraries=`
    """

    def factory(
        text: str,
        kw_map: dict[str, KeywordDoc],
        libraries: Optional[dict[str, Any]] = None,
        source: str = "/test.robot",
    ) -> tuple[Any, _ast.AST]:
        model = parse_robot(text)
        analyzer = SemanticAnalyzer(model, source, f"file://{source}")
        analyzer._library_doc = make_resource_doc(source)
        analyzer._variable_scope = VariableScope(
            command_line=[],
            own=[],
            builtin=_get_builtin_variables(),
        )
        analyzer._resolved_imports = ResolvedImports()

        # Build libraries early so the finder mock can use them for
        # realistic namespace resolution.
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
            if lib_entry.name and lib_entry.name != lib_key:
                libname_to_kws[lib_entry.name] = kw_names

        def resolve(name: str) -> Optional[KeywordDoc]:
            """Mirrors KeywordFinder._get_explicit_keyword:
            - `Greet`         -> kw_map["Greet"]
            - `MyLib.Greet`   -> only if MyLib is a known lib AND exposes Greet
            - `Unknown.Greet` -> None
            """
            if "." in name:
                ns_name, kw_name = name.split(".", 1)
                if ns_name not in libname_to_kws or kw_name not in libname_to_kws[ns_name]:
                    return None
                return kw_map.get(kw_name)
            return kw_map.get(name)

        # The KeywordFinder spec — used by the analyzer.
        finder = mocker.create_autospec(KeywordFinder, instance=True)
        finder.find_keyword.side_effect = lambda name, raise_keyword_error=True: resolve(name)
        finder.result_bdd_prefix = None
        finder.multiple_keywords_result = None
        finder.diagnostics = []

        result = analyzer.run(finder)

        # Namespace is intentionally NOT autospecced — the legacy path sets
        # attributes that aren't formally declared (`languages`, `__test_namespace__`).
        namespace = mocker.MagicMock()
        namespace.semantic_model = result.semantic_model
        namespace.libraries = libraries
        namespace.resources = {}
        namespace.languages = None
        namespace.find_keyword.side_effect = lambda name, raise_keyword_error=False, handle_bdd_style=True: resolve(
            name
        )
        namespace.finder.find_keyword.side_effect = lambda name, raise_keyword_error=False, handle_bdd_style=True: (
            resolve(name)
        )
        namespace.finder.result_bdd_prefix = None
        namespace.finder.multiple_keywords_result = None
        namespace.finder.diagnostics = []
        return namespace, model

    return factory


@pytest.fixture
def inlay_part_factory(mocker: MockerFixture) -> Callable[[InlayHintsConfig], RobotInlayHintProtocolPart]:
    """Factory: build a `RobotInlayHintProtocolPart` stub bypassing LSP setup.

    The returned stub uses a mocked `parent.documents_cache.get_namespace`
    that simply returns the namespace stashed on the document via
    `__test_namespace__`. Tests pre-stash that attribute themselves.
    """

    class _StubInlayHintPart(RobotInlayHintProtocolPart):
        def __init__(self, config: InlayHintsConfig) -> None:
            self._config = config
            self._parent_mock = mocker.MagicMock()
            self._parent_mock.documents_cache.get_namespace.side_effect = lambda doc: doc.__test_namespace__

        @property
        def parent(self) -> Any:
            return self._parent_mock

        def get_config(self, document: TextDocument) -> Optional[InlayHintsConfig]:
            return self._config

    return _StubInlayHintPart


def _attach_namespace_to_document(document: TextDocument, namespace: Any) -> None:
    """The stub inlay-hint part reads `document.__test_namespace__` instead
    of going through the LSP protocol. Centralised so tests don't have to
    repeat the `object.__setattr__` dance."""
    object.__setattr__(document, "__test_namespace__", namespace)


def _full_range(text: str) -> LspRange:
    return LspRange(
        start=Position(line=0, character=0),
        end=Position(line=text.count("\n") + 10, character=0),
    )


# --------------------------------------------------------------------------
# Pure-function tests for `_get_inlay_hint_from_semantic_tokens`.
# --------------------------------------------------------------------------


class TestGetInlayHintFromSemanticTokens:
    def test_parameter_name_hints_for_positional_args(self, mocker: MockerFixture) -> None:
        kw_doc = _kw("Log", args=[_arg("message"), _arg("level")])
        # "Log    hello    INFO" — two positional args.
        arg_tokens = [
            _semantic_token(TokenKind.ARGUMENT, "hello", line=3, col=11),
            _semantic_token(TokenKind.ARGUMENT, "INFO", line=3, col=20),
        ]
        kw_token = _semantic_token(TokenKind.KEYWORD, "Log", line=3, col=4)

        result = RobotInlayHintProtocolPart._get_inlay_hint_from_semantic_tokens(
            keyword_token=kw_token,
            kw_doc=kw_doc,
            arg_tokens=arg_tokens,
            arg_values=["hello", "INFO"],
            has_namespace_token=False,
            namespace=_make_simple_namespace_with_lib(mocker, kw_doc),
            config=_config(parameter_names=True, namespaces=False),
        )

        assert result is not None
        param_hints = [h for h in result if h.kind == InlayHintKind.PARAMETER]
        assert len(param_hints) == 2
        assert param_hints[0].label == "message="
        assert param_hints[0].position == Position(line=2, character=11)  # 0-indexed
        assert param_hints[1].label == "level="
        assert param_hints[1].position == Position(line=2, character=20)

    def test_no_parameter_hints_when_disabled(self, mocker: MockerFixture) -> None:
        kw_doc = _kw("Log", args=[_arg("message")])
        arg_tokens = [_semantic_token(TokenKind.ARGUMENT, "hello", line=3, col=11)]

        result = RobotInlayHintProtocolPart._get_inlay_hint_from_semantic_tokens(
            keyword_token=None,
            kw_doc=kw_doc,
            arg_tokens=arg_tokens,
            arg_values=["hello"],
            has_namespace_token=False,
            namespace=_make_simple_namespace_with_lib(mocker, kw_doc),
            config=_config(parameter_names=False, namespaces=False),
        )

        assert result == []

    def test_namespace_hint_when_enabled_and_no_namespace_token(self, mocker: MockerFixture) -> None:
        kw_doc = _kw("Log", libname="MyLib")
        kw_token = _semantic_token(TokenKind.KEYWORD, "Log", line=3, col=4)

        result = RobotInlayHintProtocolPart._get_inlay_hint_from_semantic_tokens(
            keyword_token=kw_token,
            kw_doc=kw_doc,
            arg_tokens=[],
            arg_values=[],
            has_namespace_token=False,
            namespace=_make_simple_namespace_with_lib(mocker, kw_doc, lib_name="MyLib"),
            config=_config(parameter_names=False, namespaces=True),
        )

        assert result is not None
        assert any(h.label == "MyLib." for h in result)
        ns_hint = next(h for h in result if h.label == "MyLib.")
        assert ns_hint.position == Position(line=2, character=4)

    def test_namespace_hint_suppressed_if_user_already_wrote_namespace(self, mocker: MockerFixture) -> None:
        kw_doc = _kw("Log", libname="MyLib")
        kw_token = _semantic_token(TokenKind.KEYWORD, "Log", line=3, col=12)

        result = RobotInlayHintProtocolPart._get_inlay_hint_from_semantic_tokens(
            keyword_token=kw_token,
            kw_doc=kw_doc,
            arg_tokens=[],
            arg_values=[],
            has_namespace_token=True,  # User wrote "MyLib." themselves.
            namespace=_make_simple_namespace_with_lib(mocker, kw_doc, lib_name="MyLib"),
            config=_config(parameter_names=False, namespaces=True),
        )

        assert result is not None
        assert not any(isinstance(h.label, str) and h.label.endswith(".") for h in result)


# --------------------------------------------------------------------------
# End-to-end smoke test: SemanticModel + collect produces hints.
# --------------------------------------------------------------------------


class TestEndToEndModelPath:
    def test_keyword_call_in_model_yields_hints(
        self,
        analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    ) -> None:
        kw_doc = _kw("My Keyword", args=[_arg("first"), _arg("second")])
        text = """\
*** Test Cases ***
T
    My Keyword    a    b
"""
        namespace, _ = analyzer_namespace_factory(text, {"My Keyword": kw_doc})
        model = namespace.semantic_model
        assert model is not None

        calls = [s for s in model.statements if isinstance(s, KeywordCallStatement)]
        assert len(calls) == 1
        call = calls[0]
        assert call.keyword_doc is not None

        arg_tokens = [t for t in call.tokens if t.kind is TokenKind.ARGUMENT]
        kw_token = next((t for t in call.tokens if t.kind is TokenKind.KEYWORD), None)
        hints = RobotInlayHintProtocolPart._get_inlay_hint_from_semantic_tokens(
            keyword_token=kw_token,
            kw_doc=call.keyword_doc,
            arg_tokens=arg_tokens,
            arg_values=[t.value for t in arg_tokens],
            has_namespace_token=any(t.kind is TokenKind.NAMESPACE for t in call.tokens),
            namespace=namespace,
            config=_config(parameter_names=True, namespaces=False),
        )

        assert hints is not None
        labels = [h.label for h in hints if h.kind == InlayHintKind.PARAMETER]
        assert labels == ["first=", "second="]


# --------------------------------------------------------------------------
# Old-vs-new equivalence: legacy `_get_inlay_hint` and the new
# `_get_inlay_hint_from_semantic_tokens` produce equivalent output for the
# same logical input.
# --------------------------------------------------------------------------


class TestLegacyVsModelEquivalence:
    @staticmethod
    def _to_rf_tokens(sem_tokens: List[SemanticToken], rf_type: str) -> List[Token]:
        return [Token(rf_type, t.value, t.line, t.col_offset) for t in sem_tokens]

    def test_param_hints_match_legacy(self, mocker: MockerFixture) -> None:
        kw_doc = _kw("Run", args=[_arg("first"), _arg("second")])
        sem_args = [
            _semantic_token(TokenKind.ARGUMENT, "x", line=3, col=11),
            _semantic_token(TokenKind.ARGUMENT, "y", line=3, col=16),
        ]
        sem_kw = _semantic_token(TokenKind.KEYWORD, "Run", line=3, col=4)
        rf_args = self._to_rf_tokens(sem_args, Token.ARGUMENT)
        rf_kw = Token(Token.KEYWORD, "Run", 3, 4)

        new_hints = RobotInlayHintProtocolPart._get_inlay_hint_from_semantic_tokens(
            keyword_token=sem_kw,
            kw_doc=kw_doc,
            arg_tokens=sem_args,
            arg_values=[t.value for t in sem_args],
            has_namespace_token=False,
            namespace=_make_simple_namespace_with_lib(mocker, kw_doc),
            config=_config(parameter_names=True, namespaces=False),
        )

        # Legacy path — call the bound method on a partially constructed
        # part instance (we only need _get_inlay_hint, no protocol setup).
        part = RobotInlayHintProtocolPart.__new__(RobotInlayHintProtocolPart)
        legacy_hints = part._get_inlay_hint(
            rf_kw,
            kw_doc,
            rf_args,
            _make_simple_namespace_with_lib(mocker, kw_doc),
            _config(parameter_names=True, namespaces=False),
        )

        assert _normalize_hints(new_hints) == _normalize_hints(legacy_hints)


# --------------------------------------------------------------------------
# End-to-end equivalence: `_collect_legacy(...)` and `_collect_from_model(...)`
# produce identical InlayHints for the same input file across the
# (parameter_names, namespaces) cross product.
# --------------------------------------------------------------------------


_E2E_CASES: list[tuple[str, str, dict[str, KeywordDoc]]] = [
    (
        "plain_keyword_call_with_args",
        """\
*** Test Cases ***
T
    Greet    Alice    Hello
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
    ),
    (
        "multiple_keyword_calls",
        """\
*** Test Cases ***
T
    Greet    Alice    Hello
    Greet    Bob    Hi
    Greet    Eve    Hey
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
    ),
    (
        "keyword_with_no_args",
        """\
*** Test Cases ***
T
    Reset
""",
        {"Reset": _kw("Reset", args=[])},
    ),
    (
        "keyword_unresolved",
        """\
*** Test Cases ***
T
    Unknown    a    b
""",
        {},
    ),
    (
        "keyword_in_keyword_def",
        """\
*** Keywords ***
My Wrapper
    Greet    Alice    Hi
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
    ),
    (
        "test_setup_fixture",
        """\
*** Test Cases ***
T
    [Setup]    Greet    Alice    Hi
    No Op
""",
        {
            "Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")]),
            "No Op": _kw("No Op", args=[]),
        },
    ),
    (
        "test_teardown_fixture",
        """\
*** Test Cases ***
T
    No Op
    [Teardown]    Greet    Bob    Bye
""",
        {
            "Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")]),
            "No Op": _kw("No Op", args=[]),
        },
    ),
    (
        "suite_setup_and_teardown",
        """\
*** Settings ***
Suite Setup       Greet    Alice    Hi
Suite Teardown    Greet    Bob    Bye

*** Test Cases ***
T
    No Op
""",
        {
            "Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")]),
            "No Op": _kw("No Op", args=[]),
        },
    ),
    (
        "test_template",
        """\
*** Settings ***
Test Template    Greet

*** Test Cases ***
T1    Alice    Hi
T2    Bob      Bye
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
    ),
    (
        "per_test_template",
        """\
*** Test Cases ***
T
    [Template]    Greet
    Alice    Hi
    Bob      Bye
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
    ),
    (
        # User wrote no namespace, library is in `namespace.libraries`.
        # Expect: namespace prefix hint when namespaces=True.
        "keyword_without_namespace_prefix",
        """\
*** Test Cases ***
T
    Greet    Alice    Hi
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")], libname="MyLib")},
    ),
    (
        # User wrote `MyLib.Greet` — namespace prefix hint must be suppressed.
        "keyword_with_namespace_prefix",
        """\
*** Test Cases ***
T
    MyLib.Greet    Alice    Hi
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")], libname="MyLib")},
    ),
    (
        # `Unknown` is NOT in namespace.libraries; both paths must agree to
        # suppress the namespace hint (user wrote *some* namespace, even if wrong).
        "keyword_with_unknown_namespace_prefix",
        """\
*** Test Cases ***
T
    Unknown.Greet    Alice    Hi
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")], libname="MyLib")},
    ),
    (
        # `Run Keyword If` carries an inner keyword call. Neither path
        # produces hints for the inner call (it's not an AST node of its own);
        # both should produce only the outer Run-Keyword-If hints.
        "run_keyword_if_inner_call_no_hints",
        """\
*** Test Cases ***
T
    Run Keyword If    ${cond}    Greet    Alice    Hi
""",
        {
            "Run Keyword If": _kw("Run Keyword If", args=[_arg("condition"), _arg("name"), _arg("*args")]),
            "Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")]),
        },
    ),
]


@pytest.mark.parametrize(("case_name", "text", "kw_map"), _E2E_CASES, ids=[c[0] for c in _E2E_CASES])
def test_collect_legacy_and_model_paths_match(
    case_name: str,
    text: str,
    kw_map: dict[str, KeywordDoc],
    axis: tuple[str, bool, bool],
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    inlay_part_factory: Callable[[InlayHintsConfig], RobotInlayHintProtocolPart],
) -> None:
    """Cross-product of all logical cases x (parameter_names, namespaces)
    toggle states. `_collect_legacy()` and `_collect_from_model()` must
    produce identical inlay-hint output.
    """
    cfg_name, parameter_names, namespaces = axis
    config = _config(parameter_names=parameter_names, namespaces=namespaces)
    namespace, ast_model = analyzer_namespace_factory(text, kw_map)
    document = _make_text_document(text)
    _attach_namespace_to_document(document, namespace)
    part = inlay_part_factory(config)

    legacy_hints = part._collect_legacy(document, _full_range(text), ast_model, namespace, config)
    assert namespace.semantic_model is not None
    model_hints = part._collect_from_model(document, _full_range(text), namespace, namespace.semantic_model, config)

    assert _normalize_hints(legacy_hints) == _normalize_hints(model_hints), (
        f"Inlay-hint mismatch in case {case_name!r} ({cfg_name}): "
        f"legacy={_normalize_hints(legacy_hints)}, model={_normalize_hints(model_hints)}"
    )


def test_library_alias_renders_alias_not_libname(
    mocker: MockerFixture,
    axis: tuple[str, bool, bool],
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    inlay_part_factory: Callable[[InlayHintsConfig], RobotInlayHintProtocolPart],
) -> None:
    """When a library is imported via `WITH NAME`, the namespace-prefix hint
    uses the alias (e.g. `Aliased.`) rather than the underlying library name.
    """
    cfg_name, parameter_names, namespaces = axis
    kw = _kw("Greet", args=[_arg("name"), _arg("greeting")], libname="MyLib")
    text = """\
*** Test Cases ***
T
    Greet    Alice    Hi
"""
    libraries = {"Aliased": _make_library_entry(mocker, "MyLib", [kw], alias="Aliased")}

    config = _config(parameter_names=parameter_names, namespaces=namespaces)
    namespace, ast_model = analyzer_namespace_factory(text, {"Greet": kw}, libraries=libraries)
    document = _make_text_document(text)
    _attach_namespace_to_document(document, namespace)
    part = inlay_part_factory(config)

    legacy_hints = part._collect_legacy(document, _full_range(text), ast_model, namespace, config)
    assert namespace.semantic_model is not None
    model_hints = part._collect_from_model(document, _full_range(text), namespace, namespace.semantic_model, config)

    assert _normalize_hints(legacy_hints) == _normalize_hints(model_hints), (
        f"Alias mismatch ({cfg_name}): legacy={_normalize_hints(legacy_hints)}, model={_normalize_hints(model_hints)}"
    )

    # Sanity for namespaces=True: alias must show up, not the original libname.
    if namespaces:
        labels = [h.label for h in (model_hints or [])]
        assert "Aliased." in labels, f"expected 'Aliased.' in {labels}"
        assert "MyLib." not in labels, f"unexpected 'MyLib.' in {labels}"


def test_run_keyword_if_outer_hints_present_inner_skipped(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    inlay_part_factory: Callable[[InlayHintsConfig], RobotInlayHintProtocolPart],
) -> None:
    """Sanity for the `run_keyword_if_inner_call_no_hints` case:
    - Outer Run-Keyword-If call DOES get a `condition=` hint
      (otherwise the equivalence test would be trivially `[] == []`).
    - INNER `Greet`'s own `name=` / `greeting=` hints are NOT emitted.
    """
    kw_map = {
        "Run Keyword If": _kw("Run Keyword If", args=[_arg("condition"), _arg("name"), _arg("*args")]),
        "Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")]),
    }
    text = """\
*** Test Cases ***
T
    Run Keyword If    ${cond}    Greet    Alice    Hi
"""
    namespace, ast_model = analyzer_namespace_factory(text, kw_map)
    assert namespace.semantic_model is not None
    config = _config(parameter_names=True, namespaces=False)
    document = _make_text_document(text)
    _attach_namespace_to_document(document, namespace)
    part = inlay_part_factory(config)

    legacy_hints = part._collect_legacy(document, _full_range(text), ast_model, namespace, config)
    model_hints = part._collect_from_model(document, _full_range(text), namespace, namespace.semantic_model, config)

    legacy_labels = [h.label for h in (legacy_hints or [])]
    model_labels = [h.label for h in (model_hints or [])]

    assert "condition=" in legacy_labels, f"legacy missing outer hint: {legacy_labels}"
    assert "condition=" in model_labels, f"model missing outer hint: {model_labels}"

    # `greeting=` is unique to the inner Greet — its absence proves the
    # inner call wasn't traversed (whereas `name=` is also a parameter of
    # `Run Keyword If` itself).
    assert "greeting=" not in legacy_labels, f"legacy leaked inner hint: {legacy_labels}"
    assert "greeting=" not in model_labels, f"model leaked inner hint: {model_labels}"


def test_library_import_init_hints_legacy_vs_model(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    inlay_part_factory: Callable[[InlayHintsConfig], RobotInlayHintProtocolPart],
) -> None:
    """LibraryImport with init args. Model path uses pre-cached
    `init_keyword_doc` on `ImportStatement`; legacy path looks the libdoc up
    via `namespace.get_imported_library_libdoc(...)`. Both produce the same
    parameter-name hints.
    """
    init_doc = _kw("__init__", args=[_arg("host"), _arg("port")])
    text = """\
*** Settings ***
Library    MyLib    localhost    8080
"""
    namespace, ast_model = analyzer_namespace_factory(text, {})
    assert namespace.semantic_model is not None

    import_stmts = [s for s in namespace.semantic_model.statements if isinstance(s, ImportStatement)]
    assert len(import_stmts) == 1
    import_stmts[0].init_keyword_doc = init_doc
    import_stmts[0].import_type = ImportType.LIBRARY

    # Legacy path needs the libdoc resolution mocked.
    lib_doc_mock = mocker.MagicMock()
    lib_doc_mock.errors = []
    lib_doc_mock.inits = [init_doc]
    namespace.get_imported_library_libdoc.return_value = lib_doc_mock
    namespace.get_resolvable_variables.return_value = {}
    namespace.imports_manager.get_libdoc_for_library_import.return_value = lib_doc_mock

    config = _config(parameter_names=True, namespaces=False)
    document = _make_text_document(text)
    _attach_namespace_to_document(document, namespace)
    part = inlay_part_factory(config)

    legacy_hints = part._collect_legacy(document, _full_range(text), ast_model, namespace, config)
    model_hints = part._collect_from_model(document, _full_range(text), namespace, namespace.semantic_model, config)

    norm_legacy = _normalize_hints(legacy_hints)
    norm_model = _normalize_hints(model_hints)

    # Sanity: legacy produced something — otherwise this test passes vacuously.
    assert any(label in ("host=", "port=") for label, _, _ in norm_legacy), (
        f"Legacy did not produce import hints, got: {norm_legacy}"
    )
    assert norm_legacy == norm_model, f"legacy={norm_legacy}, model={norm_model}"


def test_variables_import_init_hints_legacy_vs_model(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    inlay_part_factory: Callable[[InlayHintsConfig], RobotInlayHintProtocolPart],
) -> None:
    """Variables-import equivalent of the library-import test. Important on
    RF 5.0/6.x where `lib_doc.inits` for variables files is often empty.
    """
    init_doc = _kw("__init__", args=[_arg("path"), _arg("encoding")])
    text = """\
*** Settings ***
Variables    vars.py    /tmp    utf-8
"""
    namespace, ast_model = analyzer_namespace_factory(text, {})
    assert namespace.semantic_model is not None

    import_stmts = [s for s in namespace.semantic_model.statements if isinstance(s, ImportStatement)]
    assert len(import_stmts) == 1
    import_stmts[0].init_keyword_doc = init_doc
    import_stmts[0].import_type = ImportType.VARIABLES

    lib_doc_mock = mocker.MagicMock()
    lib_doc_mock.errors = []
    lib_doc_mock.inits = [init_doc]
    namespace.get_variables_import_libdoc.return_value = lib_doc_mock
    namespace.get_resolvable_variables.return_value = {}
    namespace.imports_manager.get_libdoc_for_variables_import.return_value = lib_doc_mock

    config = _config(parameter_names=True, namespaces=False)
    document = _make_text_document(text)
    _attach_namespace_to_document(document, namespace)
    part = inlay_part_factory(config)

    legacy_hints = part._collect_legacy(document, _full_range(text), ast_model, namespace, config)
    model_hints = part._collect_from_model(document, _full_range(text), namespace, namespace.semantic_model, config)

    norm_legacy = _normalize_hints(legacy_hints)
    norm_model = _normalize_hints(model_hints)
    assert any(label in ("path=", "encoding=") for label, _, _ in norm_legacy), (
        f"Legacy did not produce variables-import hints, got: {norm_legacy}"
    )
    assert norm_legacy == norm_model, f"legacy={norm_legacy}, model={norm_model}"
