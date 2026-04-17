"""Integration tests for SemanticAnalyzer.

Tests that the analyzer correctly:
- Parses RF AST models and produces AnalyzerResult with semantic_model
- Creates correct SemanticStatement types for various RF constructs
- Detects test case and keyword definitions
- Handles keyword calls, control flow, imports, settings
- Produces diagnostics compatible with NamespaceAnalyzer
"""

import io
from ast import AST
from typing import List
from unittest.mock import MagicMock

import pytest
from robot.api import get_model

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.library_doc import ResourceDoc
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import SemanticAnalyzer, _get_builtin_variables
from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType, NodeKind, TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    DefinitionStatement,
    ForStatement,
    IfStatement,
    ImportStatement,
    KeywordCallStatement,
    SemanticStatement,
    SettingStatement,
    WhileStatement,
)
from robotcode.robot.diagnostics.variable_scope import VariableScope
from robotcode.robot.utils import RF_VERSION


def _parse(text: str) -> AST:
    """Parse RF text into AST model."""
    return get_model(io.StringIO(text))  # type: ignore[no-any-return]


def _make_finder() -> KeywordFinder:
    """Create a minimal KeywordFinder mock."""
    finder = MagicMock(spec=KeywordFinder)
    finder.find_keyword.return_value = None
    finder.result_bdd_prefix = None
    finder.multiple_keywords_result = None
    finder.diagnostics = []
    return finder


def _make_resolved() -> ResolvedImports:
    """Create empty resolved imports."""
    return ResolvedImports()


def _make_resource_doc(source: str = "/test.robot") -> ResourceDoc:
    """Create a minimal ResourceDoc."""
    return ResourceDoc(name="test", source=source)


def _run_analyzer(text: str, source: str = "/test.robot") -> AnalyzerResult:
    """Parse RF text, create analyzer, skip resolve(), and run with mocked finder.

    This bypasses the real resolve() to avoid needing an ImportsManager.
    Instead, we directly set the internal state the analyzer needs.
    """
    model = _parse(text)
    analyzer = SemanticAnalyzer(model, source, f"file://{source}")

    # Bypass resolve() by setting internals directly
    library_doc = _make_resource_doc(source)
    analyzer._library_doc = library_doc
    analyzer._variable_scope = VariableScope(
        command_line=[],
        own=[],
        builtin=_get_builtin_variables(),
    )
    analyzer._resolved_imports = _make_resolved()

    finder = _make_finder()
    return analyzer.run(finder)


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
    def test_empty_file_produces_empty_model(self) -> None:
        result = _run_analyzer("")
        assert result.semantic_model is not None
        assert result.semantic_model.statements == []

    def test_result_has_semantic_model(self) -> None:
        result = _run_analyzer("*** Test Cases ***\n")
        assert result.semantic_model is not None

    def test_model_is_indexed(self) -> None:
        result = _run_analyzer(
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
    def test_single_test_case(self) -> None:
        result = _run_analyzer(
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

    def test_multiple_test_cases(self) -> None:
        result = _run_analyzer(
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

    def test_test_case_line_numbers(self) -> None:
        result = _run_analyzer(
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
    def test_single_keyword(self) -> None:
        result = _run_analyzer(
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

    def test_multiple_keywords(self) -> None:
        result = _run_analyzer(
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
    def test_keyword_call_detected(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        calls = _statements_of_kind(result, NodeKind.KEYWORD_CALL)
        assert len(calls) >= 1
        assert isinstance(calls[0], KeywordCallStatement)

    def test_multiple_keyword_calls(self) -> None:
        result = _run_analyzer(
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

    def test_keyword_call_in_keyword(self) -> None:
        result = _run_analyzer(
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
    def test_for_loop(self) -> None:
        result = _run_analyzer(
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

    def test_if_statement(self) -> None:
        result = _run_analyzer(
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

    def test_while_statement(self) -> None:
        result = _run_analyzer(
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
    def test_library_import(self) -> None:
        result = _run_analyzer(
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

    def test_resource_import(self) -> None:
        result = _run_analyzer(
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

    def test_variables_import(self) -> None:
        result = _run_analyzer(
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


# --- Settings ---


class TestSettings:
    def test_tags_setting(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
My Test
    [Tags]    smoke    regression
    Log    hello
"""
        )
        settings = _statements_of_kind(result, NodeKind.SETTING)
        tag_settings = [s for s in settings if isinstance(s, SettingStatement) and s.setting_name == "Tags"]
        assert len(tag_settings) >= 1

    def test_documentation_setting(self) -> None:
        result = _run_analyzer(
            """\
*** Settings ***
Documentation    Test suite docs
"""
        )
        settings = _statements_of_kind(result, NodeKind.SETTING)
        assert len(settings) >= 1


# --- Setup/Teardown ---


class TestSetupTeardown:
    def test_test_setup(self) -> None:
        result = _run_analyzer(
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

    def test_test_teardown(self) -> None:
        result = _run_analyzer(
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
    def test_test_template(self) -> None:
        result = _run_analyzer(
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

    def test_template_data(self) -> None:
        result = _run_analyzer(
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
    def test_variable_section_does_not_produce_statements(self) -> None:
        """Variable section variables are pre-visited but don't produce statements."""
        result = _run_analyzer(
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
    def test_empty_test_name_diagnostic(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***

    Log    hello
"""
        )
        # Should produce diagnostic about empty test name
        assert result.diagnostics is not None

    def test_empty_keyword_name_diagnostic(self) -> None:
        result = _run_analyzer(
            """\
*** Keywords ***

    Log    hello
"""
        )
        assert result.diagnostics is not None

    def test_result_has_keyword_references(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
My Test
    Log    hello
"""
        )
        assert result.keyword_references is not None

    def test_result_has_variable_references(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
My Test
    Log    ${CURDIR}
"""
        )
        assert result.variable_references is not None

    def test_result_has_test_case_definitions(self) -> None:
        result = _run_analyzer(
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
    def test_statement_at_line(self) -> None:
        result = _run_analyzer(
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

    def test_enclosing_definition_for_keyword_call(self) -> None:
        result = _run_analyzer(
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
            assert isinstance(enclosing, DefinitionStatement)
            assert enclosing.name == "My Test"


# --- Inline IF ---


class TestInlineIf:
    def test_inline_if(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
My Test
    IF    True    Log    hello
"""
        )
        ifs = _statements_of_kind(result, NodeKind.IF_HEADER)
        assert len(ifs) >= 1


# --- Complex test ---


class TestComplexScenario:
    def test_full_file(self) -> None:
        result = _run_analyzer(
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

    def test_scope_tree_produced(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
My Test
    ${x}=    Set Variable    hello
    Log    ${x}
"""
        )
        assert result.scope_tree is not None

    def test_statement_count_reasonable(self) -> None:
        """A file with 3 keyword calls should produce at least 4 statements
        (1 def + 3 calls)."""
        result = _run_analyzer(
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
    def test_typed_arguments_define_untyped_lookup_variable(self) -> None:
        result = _run_analyzer(
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

    def test_typed_argument_reference_is_not_normalized_in_usage(self) -> None:
        result = _run_analyzer(
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

    def test_complex_typed_arguments_define_untyped_lookup_variable(self) -> None:
        result = _run_analyzer(
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

    def test_complex_typed_argument_reference_is_not_normalized_in_usage(self) -> None:
        result = _run_analyzer(
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

    def test_end_statement_in_for_loop(self) -> None:
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_end_statement_in_if(self) -> None:
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_break_statement(self) -> None:
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "BREAK" for t in stmt.tokens)

    def test_continue_statement(self) -> None:
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "CONTINUE" for t in stmt.tokens)

    def test_try_header(self) -> None:
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "TRY" for t in stmt.tokens)

    def test_finally_header(self) -> None:
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "FINALLY" for t in stmt.tokens)

    def test_else_header(self) -> None:
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW and t.value == "ELSE" for t in stmt.tokens)

    def test_try_except_finally_all_present(self) -> None:
        """Verify a full TRY/EXCEPT/FINALLY/END block produces statements on all lines."""
        result = _run_analyzer(
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

    def test_for_with_break_continue_end(self) -> None:
        """FOR loop with BREAK and CONTINUE produces statements on all structural lines."""
        result = _run_analyzer(
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

    def test_model_statement_at_covers_end(self) -> None:
        """statement_at() should return a result for END lines."""
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_model_statement_at_covers_break(self) -> None:
        """statement_at() should return a result for BREAK lines."""
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.CONTROL_FLOW for t in stmt.tokens)

    def test_comment_statement(self) -> None:
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.COMMENT for t in stmt.tokens)

    def test_multiple_comments(self) -> None:
        result = _run_analyzer(
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

    def test_model_statement_at_covers_comment(self) -> None:
        """statement_at() should return a result for comment lines."""
        result = _run_analyzer(
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
        assert stmt.kind == NodeKind.UNKNOWN
        assert any(t.kind == TokenKind.COMMENT for t in stmt.tokens)
