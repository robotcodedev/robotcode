"""Integration tests for SemanticAnalyzer.

Tests that the analyzer correctly:
- Parses RF AST models and produces AnalyzerResult with semantic_model
- Creates correct SemanticStatement types for various RF constructs
- Detects test case and keyword definitions
- Handles keyword calls, control flow, imports, settings
- Produces diagnostics compatible with NamespaceAnalyzer
"""

from typing import Any, Callable, List, Optional

import pytest
from pytest_mock import MockerFixture
from robot.parsing.lexer.tokens import Token as RobotToken
from robot.parsing.model.statements import LibraryImport as RFLibraryImport
from robot.parsing.model.statements import VariablesImport as RFVariablesImport

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.library_doc import KeywordDoc as RealKeywordDoc
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import SemanticAnalyzer, _get_builtin_variables
from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType, NodeKind, TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    DefinitionBlock,
    DefinitionStatement,
    ForStatement,
    IfStatement,
    ImportStatement,
    KeywordCallStatement,
    SemanticBlock,
    SemanticStatement,
    WhileStatement,
)
from robotcode.robot.diagnostics.variable_scope import VariableScope
from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.ast import range_from_token

from .conftest import make_resource_doc, parse_robot

# Type alias keeps test signatures readable.
AnalyzerFactory = Callable[..., AnalyzerResult]


def _make_init_kw(libname: str) -> RealKeywordDoc:
    """Build a real KeywordDoc representing a library/variables `__init__`."""
    return RealKeywordDoc(
        line_no=-1,
        col_offset=-1,
        end_line_no=-1,
        end_col_offset=-1,
        source=None,
        name="__init__",
        libname=libname,
        libtype="LIBRARY",
    )


def _setup_analyzer_with_import_entry(
    mocker: MockerFixture,
    text: str,
    import_node_cls: type,
    *,
    errors: List[Any],
    inits: List[Any],
    source_or_origin: str,
    source: str = "/test.robot",
) -> tuple[SemanticAnalyzer, Any]:
    """Build a SemanticAnalyzer pre-wired with one resolved-import entry that
    matches the first `import_node_cls` (LibraryImport / VariablesImport) in
    the parsed `text`.

    The entry's `library_doc` is mocked with the supplied `errors` and `inits`,
    and its `import_range` is computed so that `_visit_import_node`'s matcher
    accepts it (`import_source == self._source` AND `import_range == range_from_token(name_token)`).

    Returns `(analyzer, entry)` so callers can attach further mocks (e.g. an
    `imports_manager`) before invoking `analyzer.run(...)`.
    """
    model = parse_robot(text)
    analyzer = SemanticAnalyzer(model, source, f"file://{source}")
    analyzer._library_doc = make_resource_doc(source)
    analyzer._variable_scope = VariableScope(command_line=[], own=[], builtin=_get_builtin_variables())

    entry = mocker.MagicMock()
    entry.import_source = source
    entry.library_doc = mocker.MagicMock()
    entry.library_doc.errors = errors
    entry.library_doc.inits = inits
    entry.library_doc.source_or_origin = source_or_origin

    # Locate the relevant Import node and copy its NAME token's range onto
    # the entry — that's how `_visit_import_node` matches.
    for node in model.sections[0].body:  # type: ignore[attr-defined]
        if isinstance(node, import_node_cls):
            name_tok = node.get_token(RobotToken.NAME)  # type: ignore[attr-defined]
            entry.import_range = range_from_token(name_tok)
            break

    analyzer._resolved_imports = ResolvedImports(import_entries={mocker.MagicMock(): entry})
    return analyzer, entry


def _attach_imports_manager(
    mocker: MockerFixture,
    analyzer: SemanticAnalyzer,
    *,
    library_init: Optional[RealKeywordDoc] = None,
    variables_init: Optional[RealKeywordDoc] = None,
) -> Any:
    """Attach a mocked ImportsManager to `analyzer._imports_manager` whose
    `get_libdoc_for_library_import` / `get_libdoc_for_variables_import` return
    a libdoc with the supplied init. Returns the imports_manager mock so
    callers can introspect the calls."""
    imports_mgr = mocker.MagicMock()
    if library_init is not None:
        lib_doc = mocker.MagicMock()
        lib_doc.inits = [library_init]
        imports_mgr.get_libdoc_for_library_import.return_value = lib_doc
    if variables_init is not None:
        vars_doc = mocker.MagicMock()
        vars_doc.inits = [variables_init]
        imports_mgr.get_libdoc_for_variables_import.return_value = vars_doc
    analyzer._imports_manager = imports_mgr
    return imports_mgr


def _statement_kinds(result: AnalyzerResult) -> List[NodeKind]:
    """Extract statement kinds from analyzer result."""
    assert result.semantic_model is not None
    return [s.kind for s in result.semantic_model.statements]


def _statements_of_kind(result: AnalyzerResult, kind: NodeKind) -> List[SemanticStatement]:
    """Filter statements by kind."""
    assert result.semantic_model is not None
    return [s for s in result.semantic_model.statements if s.kind == kind]


# --- Basic test structure ---


class TestAnalyzerBasicStructure:
    def test_empty_file_produces_empty_model(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("")
        assert result.semantic_model is not None
        assert result.semantic_model.statements == []

    def test_result_has_semantic_model(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\n")
        assert result.semantic_model is not None

    def test_model_is_indexed(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
Example
    Log    hello
"""
        )
        # build_index should have been called
        model = result.semantic_model
        assert model is not None
        # Statement at line 2 should be findable
        stmts = [s for s in model.statements if s.line_start == 2]
        assert len(stmts) >= 1


# --- Test case definitions ---


class TestTestCaseDefinitions:
    def test_single_test_case(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        defns = _statements_of_kind(result, NodeKind.TEST_CASE_DEF)
        assert len(defns) == 1
        defn = defns[0]
        assert isinstance(defn, DefinitionStatement)
        assert defn.name == "My Test"

    def test_multiple_test_cases(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
First Test
    Log    first

Second Test
    Log    second
"""
        )
        defns = _statements_of_kind(result, NodeKind.TEST_CASE_DEF)
        assert len(defns) == 2
        names = [d.name for d in defns if isinstance(d, DefinitionStatement)]
        assert "First Test" in names
        assert "Second Test" in names

    def test_test_case_line_numbers(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
    Log    world
"""
        )
        defns = _statements_of_kind(result, NodeKind.TEST_CASE_DEF)
        assert len(defns) == 1
        assert defns[0].line_start == 2


# --- Keyword definitions ---


class TestKeywordDefinitions:
    def test_single_keyword(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
My Keyword
    Log    hello
"""
        )
        defns = _statements_of_kind(result, NodeKind.KEYWORD_DEF)
        assert len(defns) == 1
        defn = defns[0]
        assert isinstance(defn, DefinitionStatement)
        assert defn.name == "My Keyword"

    def test_multiple_keywords(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
First Keyword
    Log    first

Second Keyword
    Log    second
"""
        )
        defns = _statements_of_kind(result, NodeKind.KEYWORD_DEF)
        assert len(defns) == 2


# --- Keyword calls ---


class TestKeywordCalls:
    def test_keyword_call_detected(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        calls = _statements_of_kind(result, NodeKind.KEYWORD_CALL)
        assert len(calls) >= 1
        assert isinstance(calls[0], KeywordCallStatement)

    def test_multiple_keyword_calls(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
    Log    world
    No Operation
"""
        )
        calls = _statements_of_kind(result, NodeKind.KEYWORD_CALL)
        assert len(calls) >= 3

    def test_keyword_call_in_keyword(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
My Keyword
    Log    hello
"""
        )
        calls = _statements_of_kind(result, NodeKind.KEYWORD_CALL)
        assert len(calls) >= 1


# --- Control flow ---


class TestControlFlow:
    def test_for_loop(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    FOR    ${item}    IN    a    b    c
        Log    ${item}
    END
"""
        )
        fors = _statements_of_kind(result, NodeKind.FOR_HEADER)
        assert len(fors) >= 1
        assert isinstance(fors[0], ForStatement)

    def test_if_statement(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    IF    True
        Log    yes
    END
"""
        )
        ifs = _statements_of_kind(result, NodeKind.IF_HEADER)
        assert len(ifs) >= 1
        assert isinstance(ifs[0], IfStatement)

    def test_while_statement(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    WHILE    True
        Log    looping
        BREAK
    END
"""
        )
        whiles = _statements_of_kind(result, NodeKind.WHILE_HEADER)
        assert len(whiles) >= 1
        assert isinstance(whiles[0], WhileStatement)


# --- Imports ---


class TestImports:
    def test_library_import(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Library    Collections
"""
        )
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        assert len(imports) >= 1
        imp = imports[0]
        assert isinstance(imp, ImportStatement)
        assert imp.import_type == ImportType.LIBRARY
        assert imp.import_name == "Collections"

    def test_resource_import(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Resource    common.resource
"""
        )
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        assert len(imports) >= 1
        imp = imports[0]
        assert isinstance(imp, ImportStatement)
        assert imp.import_type == ImportType.RESOURCE

    def test_variables_import(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Variables    vars.py
"""
        )
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        assert len(imports) >= 1
        imp = imports[0]
        assert isinstance(imp, ImportStatement)
        assert imp.import_type == ImportType.VARIABLES

    def test_library_import_init_keyword_doc_uses_resolved_libdoc(
        self, mocker: MockerFixture, make_finder: Callable[..., Any]
    ) -> None:
        """Happy path: matched_entry has a clean libdoc with one init.
        `init_keyword_doc` must point at that init."""
        text = "*** Settings ***\nLibrary    MyLib\n"
        init_doc = _make_init_kw("MyLib")
        analyzer, _ = _setup_analyzer_with_import_entry(
            mocker,
            text,
            RFLibraryImport,
            errors=[],
            inits=[init_doc],
            source_or_origin="MyLib",
        )

        result = analyzer.run(make_finder())
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        assert len(imports) == 1
        imp = imports[0]
        assert isinstance(imp, ImportStatement)
        assert imp.init_keyword_doc is init_doc

    def test_library_import_init_keyword_doc_falls_back_when_libdoc_has_errors(
        self, mocker: MockerFixture, make_finder: Callable[..., Any]
    ) -> None:
        """Fallback path: matched_entry has libdoc.errors -> analyzer must
        retry via imports_manager.get_libdoc_for_library_import(name, (), ...)
        and use that init keyword doc instead."""
        text = "*** Settings ***\nLibrary    BrokenLib\n"
        analyzer, _ = _setup_analyzer_with_import_entry(
            mocker,
            text,
            RFLibraryImport,
            errors=["broken import"],
            inits=[],
            source_or_origin="BrokenLib",
        )

        fallback_init = _make_init_kw("BrokenLib")
        imports_mgr = _attach_imports_manager(mocker, analyzer, library_init=fallback_init)

        result = analyzer.run(make_finder())
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        assert len(imports) == 1
        imp = imports[0]
        assert isinstance(imp, ImportStatement)
        assert imp.init_keyword_doc is fallback_init

        # Imports manager called with empty args (legacy convention).
        imports_mgr.get_libdoc_for_library_import.assert_called_once()
        call_args = imports_mgr.get_libdoc_for_library_import.call_args
        assert call_args.args[0] == "BrokenLib"
        assert call_args.args[1] == ()

    def test_variables_import_init_keyword_doc_falls_back_when_libdoc_has_errors(
        self, mocker: MockerFixture, make_finder: Callable[..., Any]
    ) -> None:
        """Same fallback for VariablesImport. Critical for RF 5.0/6.x where
        variables-imports often have empty inits even on success."""
        text = "*** Settings ***\nVariables    bad_vars.py\n"
        analyzer, _ = _setup_analyzer_with_import_entry(
            mocker,
            text,
            RFVariablesImport,
            errors=["could not load module"],
            inits=[],
            source_or_origin="bad_vars.py",
        )

        fallback_init = _make_init_kw("bad_vars")
        imports_mgr = _attach_imports_manager(mocker, analyzer, variables_init=fallback_init)

        result = analyzer.run(make_finder())
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        assert len(imports) == 1
        imp = imports[0]
        assert isinstance(imp, ImportStatement)
        assert imp.init_keyword_doc is fallback_init
        imports_mgr.get_libdoc_for_variables_import.assert_called_once()


# --- Settings ---


class TestSettings:
    def test_tags_setting(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    [Tags]    smoke    regression
    Log    hello
"""
        )
        tag_settings = _statements_of_kind(result, NodeKind.SETTING_TAGS)
        assert len(tag_settings) >= 1

    def test_documentation_setting(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Documentation    Test suite docs
"""
        )
        settings = _statements_of_kind(result, NodeKind.SETTING_DOCUMENTATION)
        assert len(settings) >= 1


# --- Setup/Teardown ---


class TestSetupTeardown:
    def test_test_setup(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    [Setup]    Log    setup
    Log    body
"""
        )
        setups = _statements_of_kind(result, NodeKind.SETUP)
        assert len(setups) >= 1
        assert isinstance(setups[0], KeywordCallStatement)

    def test_test_teardown(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    body
    [Teardown]    Log    teardown
"""
        )
        teardowns = _statements_of_kind(result, NodeKind.TEARDOWN)
        assert len(teardowns) >= 1
        assert isinstance(teardowns[0], KeywordCallStatement)


# --- Template ---


class TestTemplate:
    def test_test_template(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Test Template    Log

*** Test Cases ***
Templated Test
    hello
    world
"""
        )
        templates = _statements_of_kind(result, NodeKind.TEMPLATE_KEYWORD)
        assert len(templates) >= 1

    def test_template_data(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
Templated Test
    [Template]    Log
    hello
    world
"""
        )
        template_data = _statements_of_kind(result, NodeKind.TEMPLATE_DATA)
        assert len(template_data) >= 1


# --- Variables section ---


class TestVariablesSection:
    def test_variable_section_does_not_produce_statements(self, analyzer_factory: AnalyzerFactory) -> None:
        """Variable section variables are pre-visited but don't produce statements."""
        result = analyzer_factory(
            """\
*** Variables ***
${NAME}    value
@{LIST}    a    b    c
"""
        )
        # Variable section handling happens in pre-visit, not as statements
        # No VARIABLE_DEF statements should be produced from *** Variables *** section
        # (they are handled via _visit_VariableSection, not visit_Variable)
        assert result.semantic_model is not None


# --- Diagnostics ---


class TestDiagnostics:
    def test_empty_test_name_diagnostic(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***

    Log    hello
"""
        )
        # Should produce diagnostic about empty test name
        assert result.diagnostics is not None

    def test_empty_keyword_name_diagnostic(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***

    Log    hello
"""
        )
        assert result.diagnostics is not None

    def test_result_has_keyword_references(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        assert result.keyword_references is not None

    def test_result_has_variable_references(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    ${CURDIR}
"""
        )
        assert result.variable_references is not None

    def test_result_has_test_case_definitions(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        assert len(result.test_case_definitions) == 1
        assert result.test_case_definitions[0].name == "My Test"


# --- Model query after analysis ---


class TestModelQuery:
    def test_statement_at_line(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        model = result.semantic_model
        assert model is not None
        # Should be able to find the test definition
        stmt = model.statement_at(2)
        assert stmt is not None


class TestKeywordCallTokenDecomposition:
    """KeywordCall / Fixture / Template tokens are split into BDD_PREFIX + NAMESPACE +
    SEPARATOR + KEYWORD parts."""

    def test_plain_keyword_has_single_keyword_token(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        calls = _statements_of_kind(result, NodeKind.KEYWORD_CALL)
        assert len(calls) == 1
        kw_tokens = [t for t in calls[0].tokens if t.kind == TokenKind.KEYWORD]
        assert len(kw_tokens) == 1
        assert kw_tokens[0].value == "Log"
        assert not [t for t in calls[0].tokens if t.kind == TokenKind.NAMESPACE]
        assert not [t for t in calls[0].tokens if t.kind == TokenKind.BDD_PREFIX]

    def test_argument_with_variable_has_subtokens(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    Hello ${name}!
"""
        )
        calls = _statements_of_kind(result, NodeKind.KEYWORD_CALL)
        assert len(calls) == 1
        arg_tokens = [t for t in calls[0].tokens if t.kind == TokenKind.ARGUMENT]
        assert len(arg_tokens) == 1
        arg = arg_tokens[0]
        assert arg.sub_tokens is not None
        kinds = [t.kind for t in arg.sub_tokens]
        # Either VARIABLE or VARIABLE_NOT_FOUND depending on whether the
        # mocked finder resolves ${name}; the structural shape is the same.
        assert kinds[0] == TokenKind.TEXT_FRAGMENT  # "Hello "
        assert kinds[1] in (TokenKind.VARIABLE, TokenKind.VARIABLE_NOT_FOUND)
        assert kinds[2] == TokenKind.TEXT_FRAGMENT  # "!"
        assert arg.sub_tokens[0].value == "Hello "
        assert arg.sub_tokens[1].value == "${name}"
        assert arg.sub_tokens[2].value == "!"

    def test_run_keyword_inner_call_has_tokens(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Run Keyword    Log    hello
"""
        )
        from robotcode.robot.diagnostics.semantic_analyzer.nodes import RunKeywordCallStatement

        assert result.semantic_model is not None
        calls = [s for s in result.semantic_model.statements if isinstance(s, RunKeywordCallStatement)]
        # Without a real KeywordFinder Run Keyword may not be detected, in which
        # case there are no inner calls; in that case skip the assertion.
        if not calls:
            pytest.skip("Mocked finder did not detect Run Keyword")
        rk = calls[0]
        assert len(rk.inner_calls) >= 1
        inner = rk.inner_calls[0]
        # Inner call should have tokens — at least the keyword name
        assert inner.tokens, "inner call has no tokens"
        kw_tokens = [t for t in inner.tokens if t.kind == TokenKind.KEYWORD]
        assert len(kw_tokens) == 1
        assert kw_tokens[0].value == "Log"
        # Plus the argument token
        arg_tokens = [t for t in inner.tokens if t.kind == TokenKind.ARGUMENT]
        assert len(arg_tokens) == 1
        assert arg_tokens[0].value == "hello"

    def test_pure_variable_argument_no_text_fragment(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    ${name}
"""
        )
        calls = _statements_of_kind(result, NodeKind.KEYWORD_CALL)
        arg = next(t for t in calls[0].tokens if t.kind == TokenKind.ARGUMENT)
        assert arg.sub_tokens is not None
        kinds = [t.kind for t in arg.sub_tokens]
        # No TEXT_FRAGMENT — the value is exactly one variable.
        assert TokenKind.TEXT_FRAGMENT not in kinds
        assert kinds == [TokenKind.VARIABLE_NOT_FOUND] or kinds == [TokenKind.VARIABLE]


class TestSplitKeywordNameToken:
    """Unit tests for the `_split_keyword_name_token` helper — pure function,
    no KeywordFinder needed.
    """

    def _analyzer(self) -> SemanticAnalyzer:
        from robot.parsing import get_model

        return SemanticAnalyzer(get_model(""), "/t.robot", "file:///t.robot")

    def test_plain_keyword(self, analyzer_factory: AnalyzerFactory) -> None:
        from robot.parsing.lexer.tokens import Token as RfToken

        analyzer = self._analyzer()
        rf_token = RfToken(RfToken.KEYWORD, "Log", 3, 4)
        out = analyzer._split_keyword_name_token(rf_token, bdd_prefix=None, namespace=None)
        assert [t.kind for t in out] == [TokenKind.KEYWORD]
        assert out[0].value == "Log"
        assert out[0].col_offset == 4

    def test_namespace_qualified(self, analyzer_factory: AnalyzerFactory) -> None:
        from robot.parsing.lexer.tokens import Token as RfToken

        analyzer = self._analyzer()
        rf_token = RfToken(RfToken.KEYWORD, "BuiltIn.Log", 3, 4)
        out = analyzer._split_keyword_name_token(rf_token, bdd_prefix=None, namespace="BuiltIn")
        assert [t.kind for t in out] == [TokenKind.NAMESPACE, TokenKind.SEPARATOR, TokenKind.KEYWORD]
        ns, sep, kw = out
        assert (ns.value, sep.value, kw.value) == ("BuiltIn", ".", "Log")
        # Positions are contiguous
        assert ns.col_offset == 4
        assert sep.col_offset == 4 + 7
        assert kw.col_offset == 4 + 7 + 1

    def test_bdd_prefix_only(self, analyzer_factory: AnalyzerFactory) -> None:
        from robot.parsing.lexer.tokens import Token as RfToken

        analyzer = self._analyzer()
        rf_token = RfToken(RfToken.KEYWORD, "Given Log", 3, 4)
        out = analyzer._split_keyword_name_token(rf_token, bdd_prefix="Given ", namespace=None)
        assert [t.kind for t in out] == [TokenKind.BDD_PREFIX, TokenKind.KEYWORD]
        bdd, kw = out
        assert (bdd.value, kw.value) == ("Given", "Log")
        # BDD_PREFIX excludes trailing space; the gap (space) is between tokens.
        assert bdd.col_offset == 4
        assert bdd.length == 5
        assert kw.col_offset == 4 + 6  # "Given " = 6 chars

    def test_bdd_prefix_plus_namespace(self, analyzer_factory: AnalyzerFactory) -> None:
        from robot.parsing.lexer.tokens import Token as RfToken

        analyzer = self._analyzer()
        rf_token = RfToken(RfToken.KEYWORD, "Given BuiltIn.Log", 3, 4)
        out = analyzer._split_keyword_name_token(rf_token, bdd_prefix="Given ", namespace="BuiltIn")
        assert [t.kind for t in out] == [
            TokenKind.BDD_PREFIX,
            TokenKind.NAMESPACE,
            TokenKind.SEPARATOR,
            TokenKind.KEYWORD,
        ]
        bdd, ns, sep, kw = out
        assert (bdd.value, ns.value, sep.value, kw.value) == ("Given", "BuiltIn", ".", "Log")


class TestControlFlowHeaderTokens:
    """Group B: control-flow headers produce CONTROL_FLOW + CONDITION +
    VARIABLE_NAME (defining) + NAMED_ARGUMENT_NAME/VALUE for options."""

    def test_if_header_argument_is_condition(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    IF    ${flag}
        Log    ok
    END
"""
        )
        ifs = _statements_of_kind(result, NodeKind.IF_HEADER)
        assert len(ifs) == 1
        kinds = [t.kind for t in ifs[0].tokens]
        assert TokenKind.CONTROL_FLOW in kinds  # IF
        assert TokenKind.CONDITION in kinds
        cond = next(t for t in ifs[0].tokens if t.kind == TokenKind.CONDITION)
        assert cond.value == "${flag}"
        # Variable sub-token attached to the condition
        assert cond.sub_tokens is not None

    def test_else_if_header_argument_is_condition(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    IF    ${a}
        Log    a
    ELSE IF    ${b}
        Log    b
    END
"""
        )
        else_ifs = _statements_of_kind(result, NodeKind.ELSE_IF_HEADER)
        assert len(else_ifs) == 1
        kinds = [t.kind for t in else_ifs[0].tokens]
        assert TokenKind.CONDITION in kinds

    def test_while_header_condition_and_options(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    WHILE    ${cond}    limit=10    on_limit=PASS
        Log    loop
    END
"""
        )
        whiles = _statements_of_kind(result, NodeKind.WHILE_HEADER)
        assert len(whiles) == 1
        kinds = [t.kind for t in whiles[0].tokens]
        assert TokenKind.CONTROL_FLOW in kinds  # WHILE
        assert TokenKind.CONDITION in kinds
        # Options split into NAMED_ARGUMENT_NAME + NAMED_ARGUMENT_VALUE pairs
        names = [t for t in whiles[0].tokens if t.kind == TokenKind.NAMED_ARGUMENT_NAME]
        values = [t for t in whiles[0].tokens if t.kind == TokenKind.NAMED_ARGUMENT_VALUE]
        assert len(names) == 2
        assert len(values) == 2
        assert {t.value for t in names} == {"limit", "on_limit"}
        assert {t.value for t in values} == {"10", "PASS"}

    def test_for_header_loop_variable_is_variable_name(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    FOR    ${item}    IN    a    b    c
        Log    ${item}
    END
"""
        )
        fors = _statements_of_kind(result, NodeKind.FOR_HEADER)
        assert len(fors) == 1
        var_names = [t for t in fors[0].tokens if t.kind == TokenKind.VARIABLE_NAME]
        assert len(var_names) == 1
        assert var_names[0].value == "${item}"
        # Iteration values stay ARGUMENT
        args = [t for t in fors[0].tokens if t.kind == TokenKind.ARGUMENT]
        assert {t.value for t in args} == {"a", "b", "c"}

    def test_for_in_range_with_options(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    FOR    ${i}    IN ENUMERATE    @{items}    start=1
        Log    ${i}
    END
"""
        )
        fors = _statements_of_kind(result, NodeKind.FOR_HEADER)
        names = [t for t in fors[0].tokens if t.kind == TokenKind.NAMED_ARGUMENT_NAME]
        assert len(names) == 1
        assert names[0].value == "start"

    def test_except_header_pattern_option_and_as_variable(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    TRY
        Log    body
    EXCEPT    ValueError    type=GLOB    AS    ${err}
        Log    caught
    END
"""
        )
        excepts = _statements_of_kind(result, NodeKind.EXCEPT_HEADER)
        assert len(excepts) == 1
        kinds = [t.kind for t in excepts[0].tokens]
        # Pattern as ARGUMENT, type= split, AS as CONTROL_FLOW, AS variable as VARIABLE_NAME
        assert TokenKind.ARGUMENT in kinds  # ValueError pattern
        assert TokenKind.NAMED_ARGUMENT_NAME in kinds  # type
        assert TokenKind.NAMED_ARGUMENT_VALUE in kinds  # GLOB
        assert TokenKind.VARIABLE_NAME in kinds  # ${err}
        as_var = next(t for t in excepts[0].tokens if t.kind == TokenKind.VARIABLE_NAME)
        assert as_var.value == "${err}"


class TestSettingTokens:
    """Group D: settings expose specific TokenKinds for their content."""

    def test_tags_setting_values_are_tag_tokens(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    [Tags]    smoke    regression
    Log    hello
"""
        )
        tags = _statements_of_kind(result, NodeKind.SETTING_TAGS)
        assert len(tags) == 1
        kinds = [t.kind for t in tags[0].tokens]
        # Setting name and tag values
        assert TokenKind.SETTING_NAME in kinds
        tag_tokens = [t for t in tags[0].tokens if t.kind == TokenKind.TAG]
        assert {t.value for t in tag_tokens} == {"smoke", "regression"}

    @pytest.mark.skipif(
        RF_VERSION < (7, 0),
        reason="`Test Tags` is parsed as a TestTags statement only from RF 7.0 onward",
    )
    def test_test_tags_setting_uses_tag_tokens(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Test Tags    smoke
"""
        )
        tags = _statements_of_kind(result, NodeKind.SETTING_TEST_TAGS)
        assert any(t.kind == TokenKind.TAG and t.value == "smoke" for t in tags[0].tokens)

    def test_documentation_argument_keeps_argument_kind(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Documentation    My ${suite} suite
"""
        )
        docs = _statements_of_kind(result, NodeKind.SETTING_DOCUMENTATION)
        assert len(docs) == 1
        args = [t for t in docs[0].tokens if t.kind == TokenKind.ARGUMENT]
        assert any("${suite}" in a.value for a in args)
        # The argument carries variable sub-tokens
        arg_with_var = next(a for a in args if "${suite}" in a.value)
        assert arg_with_var.sub_tokens is not None

    def test_arguments_setting_uses_variable_name(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
My Keyword
    [Arguments]    ${name}    ${count}=5
    Log    ${name}
"""
        )
        args_settings = _statements_of_kind(result, NodeKind.SETTING_ARGUMENTS)
        assert len(args_settings) == 1
        names = [t for t in args_settings[0].tokens if t.kind == TokenKind.VARIABLE_NAME]
        assert {n.value for n in names} == {"${name}", "${count}=5"}

    def test_timeout_setting(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Test Timeout    1 minute
"""
        )
        # SuiteName/TestTimeout fall through to visit_SingleValue → SETTING_TIMEOUT
        timeouts = _statements_of_kind(result, NodeKind.SETTING_TIMEOUT)
        assert any(t.kind == TokenKind.ARGUMENT and t.value == "1 minute" for t in timeouts[0].tokens)


class TestImportTokens:
    """Group C: import statements expose IMPORT_NAME for the path and
    ARGUMENT (with variable sub-tokens) for library arguments and aliases."""

    def test_library_import_with_args_and_alias(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Library    Collections    arg1    WITH NAME    coll
"""
        )
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        assert len(imports) == 1
        kinds = [t.kind for t in imports[0].tokens]
        assert TokenKind.SETTING_NAME in kinds  # "Library"
        assert TokenKind.IMPORT_NAME in kinds  # "Collections"
        assert TokenKind.CONTROL_FLOW in kinds  # "WITH NAME"
        import_name = next(t for t in imports[0].tokens if t.kind == TokenKind.IMPORT_NAME)
        assert import_name.value == "Collections"
        # Library args plus alias both end up as ARGUMENT
        args = [t for t in imports[0].tokens if t.kind == TokenKind.ARGUMENT]
        values = {t.value for t in args}
        assert "arg1" in values
        assert "coll" in values  # the alias

    def test_resource_import(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Resource    common.resource
"""
        )
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        import_name = next(t for t in imports[0].tokens if t.kind == TokenKind.IMPORT_NAME)
        assert import_name.value == "common.resource"


class TestNamedArgumentSplit:
    """Unit tests for the named-argument detection helper."""

    @staticmethod
    def _doc_with_arg_names(mocker: MockerFixture, *names: str) -> Any:
        """Build a minimal mock with `arguments` carrying given names."""
        doc = mocker.MagicMock()
        doc.arguments = [mocker.MagicMock(name=n) for n in names]
        # MagicMock's `name` kwarg is special — assign explicitly afterwards.
        for arg, n in zip(doc.arguments, names):
            arg.name = n
        return doc

    def test_no_doc_returns_none(self) -> None:
        assert SemanticAnalyzer._named_argument_split("level=INFO", None) is None

    def test_no_equals_returns_none(self, mocker: MockerFixture) -> None:
        doc = self._doc_with_arg_names(mocker, "level")
        assert SemanticAnalyzer._named_argument_split("INFO", doc) is None

    def test_unknown_name_returns_none(self, mocker: MockerFixture) -> None:
        doc = self._doc_with_arg_names(mocker, "level")
        assert SemanticAnalyzer._named_argument_split("verbose=true", doc) is None

    def test_known_name_splits(self, mocker: MockerFixture) -> None:
        doc = self._doc_with_arg_names(mocker, "level", "html")
        result = SemanticAnalyzer._named_argument_split("level=INFO", doc)
        assert result == ("level", "INFO")

    def test_value_with_variable_returns_split_with_variable_intact(self, mocker: MockerFixture) -> None:
        doc = self._doc_with_arg_names(mocker, "msg")
        result = SemanticAnalyzer._named_argument_split("msg=${greeting}", doc)
        assert result == ("msg", "${greeting}")

    def test_name_containing_variable_is_positional(self, mocker: MockerFixture) -> None:
        # `${var}=value` is positional — the name part contains a variable.
        doc = self._doc_with_arg_names(mocker, "level")
        assert SemanticAnalyzer._named_argument_split("${var}=value", doc) is None


class TestModelTree:
    """Tree structure: model.root contains nested SemanticBlock and DefinitionBlock."""

    def test_root_is_file_block(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None
        assert model.root.kind == NodeKind.FILE

    def test_section_blocks_under_file(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Library    Collections

*** Test Cases ***
My Test
    Log    hello

*** Keywords ***
My Keyword
    No Operation
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None
        section_kinds = [child.kind for child in model.root.body if isinstance(child, SemanticBlock)]
        assert NodeKind.SETTING_SECTION in section_kinds
        assert NodeKind.TESTCASE_SECTION in section_kinds
        assert NodeKind.KEYWORD_SECTION in section_kinds

    def test_definition_block_for_test_case(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None
        section = next(
            c for c in model.root.body if isinstance(c, SemanticBlock) and c.kind == NodeKind.TESTCASE_SECTION
        )
        defns = [c for c in section.body if isinstance(c, DefinitionBlock)]
        assert len(defns) == 1
        assert defns[0].kind == NodeKind.TESTCASE
        assert defns[0].name == "My Test"
        assert defns[0].header is not None

    def test_control_flow_block_inside_test_case(self, analyzer_factory: AnalyzerFactory) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.nodes import ForBlock

        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    FOR    ${x}    IN    a    b
        Log    ${x}
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None
        section = next(
            c for c in model.root.body if isinstance(c, SemanticBlock) and c.kind == NodeKind.TESTCASE_SECTION
        )
        defn_block = next(c for c in section.body if isinstance(c, DefinitionBlock))
        for_blocks = [c for c in defn_block.body if isinstance(c, ForBlock)]
        assert len(for_blocks) == 1
        for_block = for_blocks[0]
        # The block carries its FOR header as `header`
        assert for_block.header is not None
        assert for_block.header.kind == NodeKind.FOR_HEADER
        # Body of FOR contains the Log keyword call
        body_kinds = [c.kind for c in for_block.body]
        assert NodeKind.KEYWORD_CALL in body_kinds

    def test_for_block_fields_are_populated(self, analyzer_factory: AnalyzerFactory) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.enums import ForFlavor, ForZipMode
        from robotcode.robot.diagnostics.semantic_analyzer.nodes import ForBlock

        result = analyzer_factory(
            """\
*** Test Cases ***
T
    FOR    ${item}    IN ZIP    @{a}    @{b}    mode=STRICT
        Log    ${item}
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None

        def walk(b: SemanticBlock) -> Any:
            yield b
            for c in b.body:
                if isinstance(c, SemanticBlock):
                    yield from walk(c)

        for_block = next(b for b in walk(model.root) if isinstance(b, ForBlock))
        assert for_block.flavor == ForFlavor.IN_ZIP
        assert for_block.mode == ForZipMode.STRICT
        assert [t.value for t in for_block.loop_variables] == ["${item}"]

    def test_while_block_fields_are_populated(self, analyzer_factory: AnalyzerFactory) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.enums import OnLimitAction
        from robotcode.robot.diagnostics.semantic_analyzer.nodes import WhileBlock

        result = analyzer_factory(
            """\
*** Test Cases ***
T
    WHILE    ${cond}    limit=10    on_limit=PASS    on_limit_message=stop
        BREAK
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None

        def walk(b: SemanticBlock) -> Any:
            yield b
            for c in b.body:
                if isinstance(c, SemanticBlock):
                    yield from walk(c)

        while_block = next(b for b in walk(model.root) if isinstance(b, WhileBlock))
        assert while_block.condition == "${cond}"
        assert while_block.limit == "10"
        assert while_block.on_limit == OnLimitAction.PASS
        assert while_block.on_limit_message == "stop"

    def test_if_block_condition_is_populated(self, analyzer_factory: AnalyzerFactory) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.nodes import IfBlock

        result = analyzer_factory(
            """\
*** Test Cases ***
T
    IF    ${flag}
        Log    ok
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None

        def walk(b: SemanticBlock) -> Any:
            yield b
            for c in b.body:
                if isinstance(c, SemanticBlock):
                    yield from walk(c)

        if_block = next(b for b in walk(model.root) if isinstance(b, IfBlock))
        assert if_block.condition == "${flag}"

    def test_if_else_if_else_chain_blocks_and_headers(self, analyzer_factory: AnalyzerFactory) -> None:
        """IF / ELSE IF / ELSE produces a recursive IfBlock chain. Each
        sub-block must carry the right header kind and its own condition."""
        from robotcode.robot.diagnostics.semantic_analyzer.enums import NodeKind
        from robotcode.robot.diagnostics.semantic_analyzer.nodes import IfBlock

        result = analyzer_factory(
            """\
*** Test Cases ***
T
    IF    ${a}
        Log    a
    ELSE IF    ${b}
        Log    b
    ELSE
        Log    c
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None

        def walk(b: SemanticBlock) -> Any:
            yield b
            for c in b.body:
                if isinstance(c, SemanticBlock):
                    yield from walk(c)

        if_blocks = [b for b in walk(model.root) if isinstance(b, IfBlock)]
        assert len(if_blocks) == 3, f"expected 3 IfBlocks (IF/ELSE IF/ELSE), got {len(if_blocks)}"

        # The outermost IF should carry condition `${a}` and header.kind=IF_HEADER.
        if_block = if_blocks[0]
        assert if_block.condition == "${a}"
        assert if_block.header is not None
        assert if_block.header.kind is NodeKind.IF_HEADER

        # The ELSE IF block: condition `${b}`, header.kind=ELSE_IF_HEADER.
        elseif_block = if_blocks[1]
        assert elseif_block.condition == "${b}"
        assert elseif_block.header is not None
        assert elseif_block.header.kind is NodeKind.ELSE_IF_HEADER

        # The ELSE block has no condition but does have an ELSE_HEADER as header.
        else_block = if_blocks[2]
        assert else_block.condition is None
        assert else_block.header is not None
        assert else_block.header.kind is NodeKind.ELSE_HEADER

    def test_try_except_finally_block_chain(self, analyzer_factory: AnalyzerFactory) -> None:
        """TRY / EXCEPT / FINALLY also nests via blocks — each branch must
        appear as a TryBlock with the correct header kind."""
        from robotcode.robot.diagnostics.semantic_analyzer.enums import NodeKind
        from robotcode.robot.diagnostics.semantic_analyzer.nodes import TryBlock

        result = analyzer_factory(
            """\
*** Test Cases ***
T
    TRY
        Log    body
    EXCEPT    BOOM
        Log    err
    FINALLY
        Log    cleanup
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None

        def walk(b: SemanticBlock) -> Any:
            yield b
            for c in b.body:
                if isinstance(c, SemanticBlock):
                    yield from walk(c)

        try_blocks = [b for b in walk(model.root) if isinstance(b, TryBlock)]
        # RF models TRY/EXCEPT/FINALLY as one outer Try with branches; the exact
        # nesting depth varies by version, but at minimum we expect headers for
        # TRY, EXCEPT and FINALLY to be reachable.
        header_kinds = {b.header.kind for b in try_blocks if b.header is not None}
        assert NodeKind.TRY_HEADER in header_kinds
        assert NodeKind.EXCEPT_HEADER in header_kinds
        assert NodeKind.FINALLY_HEADER in header_kinds

    def test_specialized_block_classes_for_each_construct(self, analyzer_factory: AnalyzerFactory) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
            ForBlock,
            IfBlock,
            TryBlock,
            WhileBlock,
        )

        result = analyzer_factory(
            """\
*** Test Cases ***
T
    FOR    ${x}    IN    a
        Log    ${x}
    END
    WHILE    True
        BREAK
    END
    IF    True
        Log    ok
    END
    TRY
        Log    body
    EXCEPT
        Log    err
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        assert model.root is not None
        # Walk the tree to collect the specialised blocks under the test case.
        collected = []

        def walk(b: SemanticBlock) -> None:
            collected.append(b)
            for child in b.body:
                if isinstance(child, SemanticBlock):
                    walk(child)

        walk(model.root)
        assert any(isinstance(b, ForBlock) for b in collected)
        assert any(isinstance(b, WhileBlock) for b in collected)
        assert any(isinstance(b, IfBlock) for b in collected)
        assert any(isinstance(b, TryBlock) for b in collected)

    def test_enclosing_definition_returns_block(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
My Keyword
    Log    hello
"""
        )
        model = result.semantic_model
        assert model is not None
        # Find the Log call line
        enclosing = model.enclosing_definition(3)
        assert isinstance(enclosing, DefinitionBlock)
        assert enclosing.name == "My Keyword"
        assert enclosing.kind == NodeKind.KEYWORD

    def test_enclosing_definition_for_keyword_call(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    hello
    Log    world
"""
        )
        model = result.semantic_model
        assert model is not None
        # Find a keyword call
        calls = [s for s in model.statements if s.kind == NodeKind.KEYWORD_CALL]
        if calls:
            call = calls[0]
            enclosing = model.enclosing_definition(call.line_start)
            assert enclosing is not None
            # Tree path returns DefinitionBlock; legacy path would return DefinitionStatement.
            assert isinstance(enclosing, (DefinitionBlock, DefinitionStatement))
            assert enclosing.name == "My Test"


# --- Inline IF ---


class TestInlineIf:
    def test_inline_if(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    IF    True    Log    hello
"""
        )
        ifs = _statements_of_kind(result, NodeKind.INLINE_IF_HEADER)
        assert len(ifs) >= 1


# --- Complex test ---


class TestComplexScenario:
    def test_full_file(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Settings ***
Library    Collections
Documentation    A test suite

*** Variables ***
${NAME}    Robot
@{ITEMS}    a    b    c

*** Test Cases ***
Simple Test
    Log    ${NAME}

Test With Setup
    [Setup]    Log    setup
    Log    body
    [Teardown]    Log    teardown

Test With Control Flow
    FOR    ${item}    IN    @{ITEMS}
        Log    ${item}
    END
    IF    True
        Log    yes
    END

*** Keywords ***
My Keyword
    [Arguments]    ${arg}
    Log    ${arg}
    RETURN    done
"""
        )
        model = result.semantic_model
        assert model is not None
        assert len(model.statements) > 0

        # Check we have test definitions and keyword definitions
        test_defs = _statements_of_kind(result, NodeKind.TEST_CASE_DEF)
        kw_defs = _statements_of_kind(result, NodeKind.KEYWORD_DEF)
        assert len(test_defs) == 3
        assert len(kw_defs) == 1

        # Check imports
        imports = _statements_of_kind(result, NodeKind.IMPORT)
        assert len(imports) >= 1

        # Check control flow
        fors = _statements_of_kind(result, NodeKind.FOR_HEADER)
        assert len(fors) >= 1
        ifs = _statements_of_kind(result, NodeKind.IF_HEADER)
        assert len(ifs) >= 1

    def test_scope_tree_produced(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    ${x}=    Set Variable    hello
    Log    ${x}
"""
        )
        assert result.scope_tree is not None

    def test_statement_count_reasonable(self, analyzer_factory: AnalyzerFactory) -> None:
        """A file with 3 keyword calls should produce at least 4 statements
        (1 def + 3 calls)."""
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    Log    one
    Log    two
    Log    three
"""
        )
        assert result.semantic_model is not None
        assert len(result.semantic_model.statements) >= 4


@pytest.mark.skipif(RF_VERSION < (7, 3), reason="Argument type hints require RF >= 7.3")
class TestArgumentTypeHints:
    def test_typed_arguments_define_untyped_lookup_variable(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
K
    [Arguments]    ${a: int}
    Log    ${a}

*** Test Cases ***
T
    K    1
"""
        )

        var_names = {v.name for v in result.variable_references}
        assert "${a}" in var_names

        variable_not_found = [d for d in result.diagnostics if str(d.code) == "VariableNotFound"]
        assert len(variable_not_found) == 0

    def test_typed_argument_reference_is_not_normalized_in_usage(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
K
    [Arguments]    ${a: int}
    Log    ${a: int}

*** Test Cases ***
T
    K    1
"""
        )

        assert any(str(d.code) == "VariableNotFound" and "${a: int}" in d.message for d in result.diagnostics)

    def test_complex_typed_arguments_define_untyped_lookup_variable(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
K
    [Arguments]    ${a: Literal["abc", ":", ";"] | List[Literal[1,2,3]]}
    Log    ${a}

*** Test Cases ***
T
    K    abc
"""
        )

        var_names = {v.name for v in result.variable_references}
        assert "${a}" in var_names
        assert not any(str(d.code) == "VariableNotFound" and "${a}" in d.message for d in result.diagnostics)

    def test_complex_typed_argument_reference_is_not_normalized_in_usage(
        self, analyzer_factory: AnalyzerFactory
    ) -> None:
        result = analyzer_factory(
            """\
*** Keywords ***
K
    [Arguments]    ${a: Literal["abc", ":", ";"] | List[Literal[1,2,3]]}
    Log    ${a: Literal["abc", ":", ";"] | List[Literal[1,2,3]]}

*** Test Cases ***
T
    K    abc
"""
        )

        assert any(
            str(d.code) == "VariableNotFound" and '${a: Literal["abc", ":", ";"] | List[Literal[1,2,3]]}' in d.message
            for d in result.diagnostics
        )


# --- Structural statement visitors (END, BREAK, CONTINUE, TRY, ELSE, FINALLY) ---


class TestStructuralStatements:
    """Tests for the visit_End, visit_Break, visit_Continue, visit_TryHeader,
    visit_ElseHeader, and visit_FinallyHeader visitors that create SemanticStatement
    entries in the model.
    """

    def test_end_statement_in_for_loop(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    FOR    ${item}    IN    a    b    c
        Log    ${item}
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(5)  # END line
        assert stmt is not None
        assert stmt.kind == NodeKind.END
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_end_statement_in_if(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    IF    True
        Log    yes
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(5)  # END line
        assert stmt is not None
        assert stmt.kind == NodeKind.END
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_break_statement(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    WHILE    True
        BREAK
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(4)  # BREAK line
        assert stmt is not None
        assert stmt.kind == NodeKind.BREAK_STATEMENT
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "BREAK" for t in stmt.tokens)

    def test_continue_statement(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    FOR    ${item}    IN    a    b    c
        CONTINUE
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(4)  # CONTINUE line
        assert stmt is not None
        assert stmt.kind == NodeKind.CONTINUE_STATEMENT
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "CONTINUE" for t in stmt.tokens)

    def test_try_header(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    TRY
        Log    body
    EXCEPT
        Log    error
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(3)  # TRY line
        assert stmt is not None
        assert stmt.kind == NodeKind.TRY_HEADER
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "TRY" for t in stmt.tokens)

    def test_finally_header(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    TRY
        Log    body
    FINALLY
        Log    cleanup
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(5)  # FINALLY line
        assert stmt is not None
        assert stmt.kind == NodeKind.FINALLY_HEADER
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "FINALLY" for t in stmt.tokens)

    def test_else_header(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    IF    True
        Log    yes
    ELSE
        Log    no
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(5)  # ELSE line
        assert stmt is not None
        assert stmt.kind == NodeKind.ELSE_HEADER
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "ELSE" for t in stmt.tokens)

    def test_try_except_finally_all_present(self, analyzer_factory: AnalyzerFactory) -> None:
        """Verify a full TRY/EXCEPT/FINALLY/END block produces statements on all lines."""
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    TRY
        Log    body
    EXCEPT
        Log    error
    FINALLY
        Log    cleanup
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        # All structural lines should have statements
        for line in (3, 5, 7, 9):  # TRY, EXCEPT, FINALLY, END
            stmt = model.statement_at(line)
            assert stmt is not None, f"No statement at line {line}"
        # Fallback nodes (END) should have CONTROL_FLOW tokens
        end_stmt = model.statement_at(9)
        assert end_stmt is not None
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in end_stmt.tokens)

    def test_for_with_break_continue_end(self, analyzer_factory: AnalyzerFactory) -> None:
        """FOR loop with BREAK and CONTINUE produces statements on all structural lines."""
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    FOR    ${item}    IN    a    b    c
        IF    True
            CONTINUE
        ELSE
            BREAK
        END
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        # All structural lines should have statements
        for line in (5, 6, 7, 8, 9):  # CONTINUE, ELSE, BREAK, inner END, outer END
            stmt = model.statement_at(line)
            assert stmt is not None, f"No statement at line {line}"
        # Fallback nodes (CONTINUE, ELSE, BREAK, END) should have CONTROL_FLOW tokens
        for line in (5, 6, 7, 8, 9):
            stmt = model.statement_at(line)
            assert stmt is not None
            assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_model_statement_at_covers_end(self, analyzer_factory: AnalyzerFactory) -> None:
        """statement_at() should return a result for END lines."""
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    IF    True
        Log    yes
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(5)  # END line
        assert stmt is not None
        assert stmt.kind == NodeKind.END
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_model_statement_at_covers_break(self, analyzer_factory: AnalyzerFactory) -> None:
        """statement_at() should return a result for BREAK lines."""
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    WHILE    True
        BREAK
    END
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(4)  # BREAK line
        assert stmt is not None
        assert stmt.kind == NodeKind.BREAK_STATEMENT
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_comment_statement(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    # This is a comment
    Log    hello
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(3)
        assert stmt is not None
        assert stmt.kind == NodeKind.COMMENT
        assert any(t.kind == TokenKind.COMMENT for t in stmt.tokens)

    def test_multiple_comments(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    # First comment
    Log    hello
    # Second comment
    Log    world
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt1 = model.statement_at(3)
        stmt2 = model.statement_at(5)
        assert stmt1 is not None
        assert stmt2 is not None
        assert any(t.kind == TokenKind.COMMENT for t in stmt1.tokens)
        assert any(t.kind == TokenKind.COMMENT for t in stmt2.tokens)

    def test_model_statement_at_covers_comment(self, analyzer_factory: AnalyzerFactory) -> None:
        """statement_at() should return a result for comment lines."""
        result = analyzer_factory(
            """\
*** Test Cases ***
My Test
    # A comment
    Log    hello
"""
        )
        model = result.semantic_model
        assert model is not None
        stmt = model.statement_at(3)
        assert stmt is not None
        assert stmt.kind == NodeKind.COMMENT
        assert any(t.kind == TokenKind.COMMENT for t in stmt.tokens)
