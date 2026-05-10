"""Equivalence tests for the SemanticModel-based signature help path.

Verifies that `RobotSignatureHelpProtocolPart._collect_from_model(...)`
produces SignatureHelp identical to the legacy `_collect_legacy(...)` path
across the full cross-product of keyword calls, fixtures, and library /
variables imports.

Style mirrors `test_inlay_hint_model.py` — analyzer + namespace factory
fixture, stub protocol part factory, parametrised equivalence cases.
"""

import ast as _ast
from typing import Any, Callable, List, Optional

import pytest
from pytest_mock import MockerFixture

from robotcode.core.lsp.types import Position, SignatureHelp
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.parts.signature_help import (
    RobotSignatureHelpProtocolPart,
)
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.library_doc import (
    BUILTIN_LIBRARY_NAME,
    ArgumentInfo,
    KeywordArgumentKind,
    KeywordDoc,
    LibraryDoc,
)
from robotcode.robot.diagnostics.library_doc import (
    ArgumentSpec as RobotArgumentSpec,
)
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import (
    SemanticAnalyzer,
    _get_builtin_variables,
)
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    ImportStatement,
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
    entry.library_doc = mocker.MagicMock()
    entry.library_doc.keywords = mocker.MagicMock()
    entry.library_doc.keywords.keywords = kw_docs
    entry.library_doc.errors = []
    entry.library_doc.inits = []
    entry.import_name = name
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
def signature_part_factory(
    mocker: MockerFixture,
) -> Callable[..., RobotSignatureHelpProtocolPart]:
    """Factory: build a `RobotSignatureHelpProtocolPart` stub bypassing LSP setup.

    `_collect_legacy` / `_collect_from_model` both go through
    `parent.documents_cache.get_model(document)` to obtain the AST and
    `parent.documents_cache.get_namespace(document)` to obtain the namespace.
    The stub wires both to read attributes stashed on the document itself.
    """

    class _StubSignaturePart(RobotSignatureHelpProtocolPart):
        def __init__(self) -> None:
            self._parent_mock = mocker.MagicMock()
            self._parent_mock.documents_cache.get_namespace.side_effect = lambda doc: doc.__test_namespace__
            self._parent_mock.documents_cache.get_model.side_effect = lambda doc, *args, **kwargs: doc.__test_ast__

        @property
        def parent(self) -> Any:
            return self._parent_mock

    def factory() -> RobotSignatureHelpProtocolPart:
        return _StubSignaturePart()

    return factory


def _attach_to_document(document: TextDocument, namespace: Any, ast_model: _ast.AST) -> None:
    object.__setattr__(document, "__test_namespace__", namespace)
    object.__setattr__(document, "__test_ast__", ast_model)


# --------------------------------------------------------------------------
# Equivalence-comparison helper: SignatureHelp dataclasses contain
# documentation Markdown that depends on libdoc/parent state we don't mock.
# Strip docs/types and keep the structural fields that user-facing behaviour
# depends on.
# --------------------------------------------------------------------------


def _normalize(sig: Optional[SignatureHelp]) -> Any:
    if sig is None:
        return None
    return {
        "active_signature": sig.active_signature,
        "active_parameter": sig.active_parameter,
        "signatures": [
            {
                "label": s.label,
                "active_parameter": s.active_parameter,
                "parameters": ([{"label": p.label} for p in (s.parameters or [])]),
            }
            for s in (sig.signatures or [])
        ],
    }


# --------------------------------------------------------------------------
# Cases
# --------------------------------------------------------------------------


_CASES: list[tuple[str, str, dict[str, KeywordDoc], list[tuple[int, int]]]] = [
    (
        "keyword_call_first_arg",
        """\
*** Test Cases ***
T
    Greet    Alice    Hello
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        [
            (2, 13),  # cursor on first arg
            (2, 22),  # cursor on second arg
            (2, 28),  # cursor past second arg (next slot)
        ],
    ),
    (
        "keyword_call_named_arg",
        """\
*** Test Cases ***
T
    Greet    name=Alice    greeting=Hello
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        [
            (2, 18),  # cursor on name=Alice value
            (2, 36),  # cursor on greeting=Hello value
        ],
    ),
    (
        "keyword_call_cursor_on_name_returns_none",
        """\
*** Test Cases ***
T
    Greet    Alice
""",
        {"Greet": _kw("Greet", args=[_arg("name")])},
        [
            (2, 4),  # cursor right at start of "Greet" → None
            (2, 6),  # cursor inside "Greet" → None
            (2, 9),  # cursor right after "Greet" (within +2 grace) → None
        ],
    ),
    (
        "keyword_call_no_args",
        """\
*** Test Cases ***
T
    Reset
""",
        {"Reset": _kw("Reset", args=[])},
        [
            (2, 14),  # cursor far past keyword name
        ],
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
        [
            (2, 25),  # cursor on first arg of Setup keyword
            (2, 34),  # cursor on second arg
        ],
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
        [
            (3, 28),  # cursor on first arg
            (3, 35),  # cursor on second arg
        ],
    ),
    (
        "keyword_call_with_assignment",
        """\
*** Test Cases ***
T
    ${result}=    Greet    Alice    Hi
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        [
            (2, 27),  # cursor on first arg after assignment
            (2, 37),  # cursor on second arg
        ],
    ),
    (
        "keyword_call_in_keyword_def",
        """\
*** Keywords ***
My Wrapper
    Greet    Alice    Hi
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        [
            (2, 13),  # cursor on first arg
            (2, 22),  # cursor on second arg
        ],
    ),
    (
        # Variable references in arguments do not change which positional
        # arg the cursor is on — both paths must agree.
        "keyword_call_with_variable_in_arg",
        """\
*** Test Cases ***
T
    Greet    ${name}    Hello
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        [
            (2, 13),  # cursor inside ${name}
            (2, 24),  # cursor on second arg "Hello"
        ],
    ),
    (
        # `[Setup]    NONE` is the special "no setup" marker. Both paths
        # must return None gracefully — no signature help, no crash.
        "setup_with_NONE_marker",
        """\
*** Test Cases ***
T
    [Setup]    NONE
    No Op
""",
        {"No Op": _kw("No Op", args=[])},
        [
            (2, 16),  # cursor on the "NONE" word
            (2, 20),  # cursor past "NONE"
        ],
    ),
    (
        # Multi-line keyword call with `...` continuation. The arg-index
        # math has dedicated branches for CONTINUATION tokens — exercise them.
        "keyword_call_multiline_continuation",
        """\
*** Test Cases ***
T
    Greet    Alice
    ...    Hello
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        [
            (2, 13),  # cursor on first arg "Alice"
            (3, 12),  # cursor on continuation "Hello"
            (3, 18),  # cursor past continuation arg
        ],
    ),
    (
        # Fall-through case: TestTemplate / Template have no legacy handler,
        # so both paths must return None even though the model could in
        # principle resolve a template keyword. Bug parity, not improvement.
        "test_template_no_signature_help",
        """\
*** Settings ***
Test Template    Greet
""",
        {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        [
            (1, 25),  # cursor far past "Greet" inside the TestTemplate value
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
    signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
) -> None:
    namespace, ast_model = analyzer_namespace_factory(text, kw_map)
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = signature_part_factory()

    for line, char in positions:
        position = Position(line=line, character=char)

        # Legacy path: bypass `collect()`'s flag check by calling the leaf
        # method directly, so we get legacy output regardless of the
        # `semantic_model` attribute on the namespace.
        legacy = part._collect_legacy(document, position, None)
        model = part._collect_from_model(document, position, namespace, namespace.semantic_model)

        assert _normalize(legacy) == _normalize(model), (
            f"{name} @ ({line},{char}): legacy != model\n  legacy={_normalize(legacy)}\n  model ={_normalize(model)}"
        )


# --------------------------------------------------------------------------
# Targeted tests for parts of the model path that don't have a simple
# legacy mirror — these document semantic correctness, not equivalence.
# --------------------------------------------------------------------------


class TestModelPathDirectBehaviour:
    def test_no_signature_help_outside_known_statement(
        self,
        analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
        signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
    ) -> None:
        text = "*** Settings ***\nDocumentation    text here\n*** Test Cases ***\nT\n    No Op\n"
        namespace, ast_model = analyzer_namespace_factory(text, {"No Op": _kw("No Op", args=[])})
        document = _make_text_document(text)
        _attach_to_document(document, namespace, ast_model)

        part = signature_part_factory()
        # Cursor inside Documentation setting — model path returns None
        # (Documentation is not a KeywordCall / Fixture / Import).
        result = part._collect_from_model(
            document,
            Position(line=1, character=20),
            namespace,
            namespace.semantic_model,
        )
        assert result is None

    def test_keyword_call_cursor_on_first_arg_returns_signature(
        self,
        analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
        signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
    ) -> None:
        text = "*** Test Cases ***\nT\n    Greet    Alice    Hello\n"
        namespace, ast_model = analyzer_namespace_factory(
            text,
            {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        )
        document = _make_text_document(text)
        _attach_to_document(document, namespace, ast_model)

        part = signature_part_factory()
        result = part._collect_from_model(
            document,
            Position(line=2, character=13),  # cursor on "Alice"
            namespace,
            namespace.semantic_model,
        )
        assert result is not None
        assert result.active_parameter == 0

    def test_keyword_call_cursor_on_second_arg_returns_index_one(
        self,
        analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
        signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
    ) -> None:
        text = "*** Test Cases ***\nT\n    Greet    Alice    Hello\n"
        namespace, ast_model = analyzer_namespace_factory(
            text,
            {"Greet": _kw("Greet", args=[_arg("name"), _arg("greeting")])},
        )
        document = _make_text_document(text)
        _attach_to_document(document, namespace, ast_model)

        part = signature_part_factory()
        result = part._collect_from_model(
            document,
            Position(line=2, character=22),  # cursor on "Hello"
            namespace,
            namespace.semantic_model,
        )
        assert result is not None
        assert result.active_parameter == 1

    def test_keyword_call_with_no_keyword_doc_returns_none(
        self,
        analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
        signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
    ) -> None:
        # Unresolved keyword — no keyword_doc, no signature help.
        text = "*** Test Cases ***\nT\n    Unknown Keyword    a    b\n"
        namespace, ast_model = analyzer_namespace_factory(text, {})
        document = _make_text_document(text)
        _attach_to_document(document, namespace, ast_model)

        part = signature_part_factory()
        result = part._collect_from_model(
            document,
            Position(line=2, character=23),
            namespace,
            namespace.semantic_model,
        )
        assert result is None


# --------------------------------------------------------------------------
# Smoke test — `collect()` chooses the model path when semantic_model exists.
# --------------------------------------------------------------------------


def test_collect_dispatches_to_model_path_when_semantic_model_available(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
) -> None:
    text = "*** Test Cases ***\nT\n    Greet    Alice\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Greet": _kw("Greet", args=[_arg("name")])})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = signature_part_factory()
    spy_model = mocker.spy(part, "_collect_from_model")
    spy_legacy = mocker.spy(part, "_collect_legacy")

    part.collect(part, document, Position(line=2, character=13), None)

    assert spy_model.called
    assert not spy_legacy.called


def test_collect_dispatches_to_legacy_path_when_no_semantic_model(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
) -> None:
    text = "*** Test Cases ***\nT\n    Greet    Alice\n"
    namespace, ast_model = analyzer_namespace_factory(text, {"Greet": _kw("Greet", args=[_arg("name")])})
    namespace.semantic_model = None  # Simulate flag OFF
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = signature_part_factory()
    spy_model = mocker.spy(part, "_collect_from_model")
    spy_legacy = mocker.spy(part, "_collect_legacy")

    part.collect(part, document, Position(line=2, character=13), None)

    assert not spy_model.called
    assert spy_legacy.called


# --------------------------------------------------------------------------
# Library / Variables import: verify init_keyword_doc resolution path.
# --------------------------------------------------------------------------


def _make_lib_entry_with_inits(mocker: MockerFixture, name: str, init_kw: KeywordDoc) -> Any:
    entry = _make_library_entry(mocker, name, [], alias=None)
    entry.library_doc.inits = [init_kw]
    entry.import_name = name
    return entry


def test_library_import_init_signature_help_via_model(
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
) -> None:
    """When the analyzer has populated `init_keyword_doc` on an
    ImportStatement, `_collect_from_model` should produce signature help
    pointing at the init's parameters."""
    init_kw = _kw("__init__", args=[_arg("path"), _arg("encoding")], libname="MyLib")
    text = "*** Settings ***\nLibrary    MyLib    /path    utf-8\n"
    namespace, ast_model = analyzer_namespace_factory(text, {})

    # Attach the init_keyword_doc to the analyzer-built ImportStatement.
    import_stmt = next(s for s in namespace.semantic_model.statements if isinstance(s, ImportStatement))
    import_stmt.init_keyword_doc = init_kw

    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = signature_part_factory()
    result = part._collect_from_model(
        document,
        Position(line=1, character=23),  # cursor on first arg "/path"
        namespace,
        namespace.semantic_model,
    )

    assert result is not None
    assert result.active_parameter == 0


def test_resource_import_does_not_get_signature_help(
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
) -> None:
    """Resource imports have no init signature — even if init_keyword_doc
    were somehow set, the model path filters by import_type and skips them."""
    text = "*** Settings ***\nResource    common.resource\n"
    namespace, ast_model = analyzer_namespace_factory(text, {})
    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = signature_part_factory()
    result = part._collect_from_model(
        document,
        Position(line=1, character=22),
        namespace,
        namespace.semantic_model,
    )
    assert result is None


# --------------------------------------------------------------------------
# Library / Variables import equivalence: legacy looks up the libdoc via
# `namespace.get_imported_library_libdoc(...)` / `get_variables_import_libdoc(...)`,
# the model reads `init_keyword_doc` straight off the statement. Both paths
# must produce the same SignatureHelp for the same input.
# --------------------------------------------------------------------------


_IMPORT_CASES: list[tuple[str, str, str, list[tuple[int, int]]]] = [
    (
        # Cursor on the import path NAME token: legacy returns None
        # (position <= name_token.end + 1), model mirrors that guard.
        "library_import_cursor_on_path_returns_none",
        "library",
        "*** Settings ***\nLibrary    MyLib    /path    utf-8\n",
        [
            (1, 12),  # cursor on "MyLib"
            (1, 14),  # cursor inside "MyLib"
            (1, 16),  # cursor on the trailing 'b' of "MyLib"
        ],
    ),
    (
        "library_import_cursor_on_first_arg",
        "library",
        "*** Settings ***\nLibrary    MyLib    /path    utf-8\n",
        [
            (1, 23),  # cursor on "/path"
            (1, 31),  # cursor on "utf-8" (second arg)
        ],
    ),
    (
        # Library import with WITH NAME alias: cursor on the alias keyword
        # and on the alias name itself must return None for both paths.
        "library_import_with_name_alias_returns_none_past_alias",
        "library",
        "*** Settings ***\nLibrary    MyLib    /path    WITH NAME    Aliased\n",
        [
            (1, 35),  # cursor on "WITH NAME"
            (1, 50),  # cursor on the alias "Aliased"
        ],
    ),
    (
        # But cursor on the args BEFORE WITH NAME still produces signature help.
        "library_import_with_name_alias_args_before_alias",
        "library",
        "*** Settings ***\nLibrary    MyLib    /path    WITH NAME    Aliased\n",
        [
            (1, 23),  # cursor on "/path" — should give signature
        ],
    ),
    (
        "variables_import_cursor_on_path_returns_none",
        "variables",
        "*** Settings ***\nVariables    vars.py    /var\n",
        [
            (1, 14),  # cursor inside "vars.py"
        ],
    ),
    (
        "variables_import_cursor_on_first_arg",
        "variables",
        "*** Settings ***\nVariables    vars.py    /var\n",
        [
            (1, 25),  # cursor on "/var"
        ],
    ),
]


@pytest.mark.parametrize(
    ("name", "import_kind", "text", "positions"),
    _IMPORT_CASES,
    ids=[c[0] for c in _IMPORT_CASES],
)
def test_imports_legacy_and_model_paths_match(
    name: str,
    import_kind: str,
    text: str,
    positions: list[tuple[int, int]],
    mocker: MockerFixture,
    analyzer_namespace_factory: Callable[..., tuple[Any, _ast.AST]],
    signature_part_factory: Callable[..., RobotSignatureHelpProtocolPart],
) -> None:
    """Both the legacy AST-walk path and the model path resolve the import
    init keyword. They go through different APIs (`get_imported_library_libdoc`
    vs. `stmt.init_keyword_doc`) but must produce the same SignatureHelp."""
    init_kw = _kw(
        "__init__",
        args=[_arg("path"), _arg("encoding")],
        libname="MyLib" if import_kind == "library" else "vars.py",
    )

    namespace, ast_model = analyzer_namespace_factory(text, {})

    # Wire the legacy lookup so it returns a libdoc with our init kw_doc.
    fake_lib_doc = mocker.MagicMock(spec=LibraryDoc)
    fake_lib_doc.errors = []
    fake_lib_doc.inits = [init_kw]
    if import_kind == "library":
        namespace.get_imported_library_libdoc.return_value = fake_lib_doc
    else:
        namespace.get_variables_import_libdoc.return_value = fake_lib_doc
    namespace.get_resolvable_variables.return_value = {}
    namespace.imports_manager = mocker.MagicMock()

    # Wire the model lookup: stash init_keyword_doc on the ImportStatement.
    import_stmt = next(s for s in namespace.semantic_model.statements if isinstance(s, ImportStatement))
    import_stmt.init_keyword_doc = init_kw

    document = _make_text_document(text)
    _attach_to_document(document, namespace, ast_model)

    part = signature_part_factory()

    for line, char in positions:
        position = Position(line=line, character=char)
        legacy = part._collect_legacy(document, position, None)
        model = part._collect_from_model(document, position, namespace, namespace.semantic_model)
        assert _normalize(legacy) == _normalize(model), (
            f"{name} @ ({line},{char}): legacy != model\n  legacy={_normalize(legacy)}\n  model ={_normalize(model)}"
        )
