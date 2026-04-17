"""Unit tests for nested variable name resolution.

Tests that _try_resolve_nested_variable_base and _resolve_variable_to_string
correctly resolve nested variables in variable names — both in the *** Variables ***
section and in VAR statements — following RF's replace_string behavior.

Also includes parity tests that verify both SemanticAnalyzer and NamespaceAnalyzer
produce identical results for nested variable name resolution.
"""

import io
from ast import AST
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from robot.api import get_model

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.entities import VariableDefinition
from robotcode.robot.diagnostics.errors import Error
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.library_doc import ResourceDoc
from robotcode.robot.diagnostics.namespace_analyzer import NamespaceAnalyzer
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import SemanticAnalyzer, _get_builtin_variables
from robotcode.robot.diagnostics.variable_scope import VariableScope
from robotcode.robot.utils import RF_VERSION


def _parse(text: str) -> AST:
    return get_model(io.StringIO(text))  # type: ignore[no-any-return]


def _make_finder() -> KeywordFinder:
    finder = MagicMock(spec=KeywordFinder)
    finder.find_keyword.return_value = None
    finder.result_bdd_prefix = None
    finder.multiple_keywords_result = None
    finder.diagnostics = []
    return finder


def _prepare_analyzer(analyzer: SemanticAnalyzer | NamespaceAnalyzer, source: str) -> None:
    analyzer._library_doc = ResourceDoc(name="test", source=source)
    analyzer._variable_scope = VariableScope(
        command_line=[],
        own=[],
        builtin=_get_builtin_variables(),
    )
    analyzer._resolved_imports = ResolvedImports()


def _run_analyzer(text: str, source: str = "/test.robot") -> AnalyzerResult:
    model = _parse(text)
    analyzer = SemanticAnalyzer(model, source, f"file://{source}")
    _prepare_analyzer(analyzer, source)
    return analyzer.run(_make_finder())


def _run_both(text: str, source: str = "/test.robot") -> tuple[AnalyzerResult, AnalyzerResult]:
    """Run both analyzers on the same text. Returns (semantic_result, namespace_result)."""
    model_s = _parse(text)
    model_n = _parse(text)

    semantic = SemanticAnalyzer(model_s, source, f"file://{source}")
    namespace = NamespaceAnalyzer(model_n, source, f"file://{source}")

    _prepare_analyzer(semantic, source)
    _prepare_analyzer(namespace, source)

    return semantic.run(_make_finder()), namespace.run(_make_finder())


def _var_names(result: AnalyzerResult) -> Dict[str, VariableDefinition]:
    """Return a dict mapping variable name → VariableDefinition from the result."""
    return {v.name: v for v in result.variable_references}


def _diagnostic_codes(result: AnalyzerResult) -> List[str]:
    """Return all diagnostic codes as strings."""
    return [str(d.code) for d in result.diagnostics if d.code]


def _diagnostics_with_code(result: AnalyzerResult, code: str) -> List[object]:
    """Return diagnostics matching a specific error code."""
    return [d for d in result.diagnostics if str(d.code) == code]


# ──────────────────────────────────────────────────────────────────────
#  *** Variables *** section — nested variable name resolution
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="Nested variable names require RF >= 7.0")
class TestVariablesSectionNestedResolution:
    """Tests for nested variable name resolution in *** Variables *** section."""

    def test_scalar_variable_resolved_in_name(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1
${NESTED ${A}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names

    def test_multi_value_variable_joined_with_space(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${MULTI}    a    b    c
${NESTED ${MULTI}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED a b c}" in names

    def test_list_variable_resolved_to_str_list(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
@{LIST}    x    y    z
${NESTED @{LIST}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED ['x', 'y', 'z']}" in names

    def test_dict_variable_resolved_to_str_dict(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
&{DICT}    a=1    b=2
${NESTED &{DICT}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED {'a': '1', 'b': '2'}}" in names

    def test_dict_accessed_as_list_returns_keys(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
&{DICT}    a=1    b=2    c=3
${NESTED @{DICT}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED ['a', 'b', 'c']}" in names

    def test_env_variable_with_default_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED %{UNLIKELY_ROBOTCODE_TEST_VAR=fallback}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED fallback}" in names

    def test_expression_produces_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${{1+1}}}    value
"""
        )
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(hints) >= 1

    def test_unknown_variable_produces_error(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${UNKNOWN}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        assert len(errors) >= 1

    def test_empty_nested_variable_produces_error(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        assert len(errors) >= 1

    def test_recursive_resolution(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1
${B}    ${A}
${NESTED ${B}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names

    def test_multiple_nested_vars_in_name(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${X}    hello
${Y}    world
${NESTED ${X}_${Y}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED hello_world}" in names

    def test_no_diagnostic_for_successful_resolution(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1
${NESTED ${A}}    value
"""
        )
        hint_codes = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        resolve_codes = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        assert len(hint_codes) == 0
        assert len(resolve_codes) == 0


# ──────────────────────────────────────────────────────────────────────
#  VAR statement — nested variable name resolution
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="VAR statements require RF >= 7.0")
class TestVarStatementNestedResolution:
    """Tests for nested variable name resolution in VAR statements."""

    def test_scalar_variable_resolved_in_var_name(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1

*** Test Cases ***
Example
    VAR    ${NESTED ${A}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names

    def test_multi_value_joined_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${MULTI}    a    b    c

*** Test Cases ***
Example
    VAR    ${NESTED ${MULTI}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED a b c}" in names

    def test_list_variable_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
@{LIST}    x    y    z

*** Test Cases ***
Example
    VAR    ${NESTED @{LIST}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED ['x', 'y', 'z']}" in names

    def test_dict_variable_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
&{DICT}    a=1    b=2

*** Test Cases ***
Example
    VAR    ${NESTED &{DICT}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED {'a': '1', 'b': '2'}}" in names

    def test_dict_as_list_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
&{DICT}    a=1    b=2    c=3

*** Test Cases ***
Example
    VAR    ${NESTED @{DICT}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED ['a', 'b', 'c']}" in names

    def test_env_variable_with_default_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED %{UNLIKELY_ROBOTCODE_TEST_VAR=fallback}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED fallback}" in names

    def test_expression_in_var_statement_produces_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${{1+1}}}    value
"""
        )
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(hints) >= 1

    def test_unknown_variable_in_var_statement_produces_error(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${UNKNOWN}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        assert len(errors) >= 1

    def test_empty_nested_in_var_statement_produces_error(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        assert len(errors) >= 1

    def test_recursive_resolution_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1
${B}    ${A}

*** Test Cases ***
Example
    VAR    ${NESTED ${B}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names

    def test_var_scope_suite_with_nested_name(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1

*** Test Cases ***
Example
    VAR    ${NESTED ${A}}    value    scope=SUITE
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names

    def test_var_scope_global_with_nested_name(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1

*** Test Cases ***
Example
    VAR    ${NESTED ${A}}    value    scope=GLOBAL
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names

    def test_no_diagnostic_for_successful_var_resolution(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1

*** Test Cases ***
Example
    VAR    ${NESTED ${A}}    value
"""
        )
        hint_codes = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        error_codes = [d for d in result.diagnostics if str(d.code) == Error.VARIABLE_NAME_NOT_RESOLVABLE]
        assert len(hint_codes) == 0
        assert len(error_codes) == 0

    def test_var_in_keyword_with_nested_name(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1

*** Keywords ***
My Keyword
    VAR    ${NESTED ${A}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names


# ──────────────────────────────────────────────────────────────────────
#  Parity helpers — compare SemanticAnalyzer vs NamespaceAnalyzer
# ──────────────────────────────────────────────────────────────────────


def _diag_signature(result: Any) -> list[tuple[int, int, int, int, str, Any, Any]]:
    return sorted(
        (
            d.range.start.line,
            d.range.start.character,
            d.range.end.line,
            d.range.end.character,
            d.message,
            d.severity,
            d.code,
        )
        for d in result.diagnostics
    )


def _var_refs_signature(result: Any) -> list[tuple[str, str, tuple[tuple[int, int, int, int], ...]]]:
    items: list[tuple[str, str, tuple[tuple[int, int, int, int], ...]]] = []
    for var_def, locations in result.variable_references.items():
        loc_sig = tuple(
            sorted(
                (loc.range.start.line, loc.range.start.character, loc.range.end.line, loc.range.end.character)
                for loc in locations
            )
        )
        items.append((var_def.name, var_def.type.value, loc_sig))
    return sorted(items)


def _scope_tree_signature(result: Any) -> list[tuple[str, int, int, int, int, int]]:
    items: list[tuple[str, int, int, int, int, int]] = []
    for scope in result.scope_tree.local_scopes:
        items.append(
            (
                scope.name,
                scope.range.start.line,
                scope.range.start.character,
                scope.range.end.line,
                scope.range.end.character,
                len(scope.variables),
            )
        )
    return sorted(items)


def _assert_nested_var_parity(semantic_result: Any, namespace_result: Any) -> None:
    """Assert diagnostics, variable references, and scope tree match."""
    assert _diag_signature(semantic_result) == _diag_signature(namespace_result), "diagnostics mismatch"
    assert _var_refs_signature(semantic_result) == _var_refs_signature(namespace_result), "variable_references mismatch"
    assert _scope_tree_signature(semantic_result) == _scope_tree_signature(namespace_result), "scope_tree mismatch"


# ──────────────────────────────────────────────────────────────────────
#  Parity tests — *** Variables *** section
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="Nested variable names require RF >= 7.0")
class TestVariablesSectionNestedParity:
    """Both analyzers must produce identical results for nested variable names."""

    def test_scalar_resolution_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${A}    1
${NESTED ${A}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_multi_value_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${MULTI}    a    b    c
${NESTED ${MULTI}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_list_variable_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
@{LIST}    x    y    z
${NESTED @{LIST}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_dict_variable_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
&{DICT}    a=1    b=2
${NESTED &{DICT}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_dict_as_list_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
&{DICT}    a=1    b=2    c=3
${NESTED @{DICT}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_env_variable_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED %{UNLIKELY_ROBOTCODE_TEST_VAR=fallback}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_expression_hint_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${{1+1}}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_unknown_variable_error_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${UNKNOWN}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_empty_nested_error_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_recursive_resolution_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${A}    1
${B}    ${A}
${NESTED ${B}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_multiple_nested_vars_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${X}    hello
${Y}    world
${NESTED ${X}_${Y}}    value
"""
        )
        _assert_nested_var_parity(s, n)


# ──────────────────────────────────────────────────────────────────────
#  Parity tests — VAR statements
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="VAR statements require RF >= 7.0")
class TestVarStatementNestedParity:
    """Both analyzers must produce identical results for VAR with nested names."""

    def test_scalar_resolution_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${A}    1

*** Test Cases ***
Example
    VAR    ${NESTED ${A}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_list_variable_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
@{LIST}    x    y    z

*** Test Cases ***
Example
    VAR    ${NESTED @{LIST}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_dict_variable_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
&{DICT}    a=1    b=2

*** Test Cases ***
Example
    VAR    ${NESTED &{DICT}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_dict_as_list_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
&{DICT}    a=1    b=2    c=3

*** Test Cases ***
Example
    VAR    ${NESTED @{DICT}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_expression_hint_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${{1+1}}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_unknown_variable_error_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${UNKNOWN}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_empty_nested_error_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_var_scope_suite_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${A}    1

*** Test Cases ***
Example
    VAR    ${NESTED ${A}}    value    scope=SUITE
"""
        )
        _assert_nested_var_parity(s, n)

    def test_var_scope_global_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${A}    1

*** Test Cases ***
Example
    VAR    ${NESTED ${A}}    value    scope=GLOBAL
"""
        )
        _assert_nested_var_parity(s, n)

    def test_var_in_keyword_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${A}    1

*** Keywords ***
My Keyword
    VAR    ${NESTED ${A}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_recursive_in_var_statement_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${A}    1
${B}    ${A}

*** Test Cases ***
Example
    VAR    ${NESTED ${B}}    value
"""
        )
        _assert_nested_var_parity(s, n)


# ──────────────────────────────────────────────────────────────────────
#  Number literal tests — *** Variables *** section
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="Nested variable names require RF >= 7.0")
class TestVariablesSectionNumberLiterals:
    """Tests for number literal resolution in nested variable names (Variables section)."""

    def test_integer_literal_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${1}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names

    def test_negative_integer_literal_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${-42}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED -42}" in names

    def test_float_literal_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${3.14}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 3.14}" in names

    def test_hex_literal_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${0xFF}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 255}" in names

    def test_octal_literal_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${0o17}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 15}" in names

    def test_binary_literal_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${0b1010}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 10}" in names

    def test_number_literal_no_error_diagnostic(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${1}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) == 0

    def test_zero_literal_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${0}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 0}" in names

    def test_scientific_notation_resolved(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${1e3}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1000.0}" in names

    def test_number_with_spaces_resolved(self) -> None:
        """RF normalizes by stripping spaces before number parsing."""
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${ 42 }}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 42}" in names


# ──────────────────────────────────────────────────────────────────────
#  Number literal tests — VAR statements
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="VAR statements require RF >= 7.0")
class TestVarStatementNumberLiterals:
    """Tests for number literal resolution in nested variable names (VAR statements)."""

    def test_integer_literal_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${1}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names

    def test_negative_integer_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${-42}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED -42}" in names

    def test_float_literal_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${3.14}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 3.14}" in names

    def test_hex_literal_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${0xFF}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 255}" in names

    def test_octal_literal_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${0o17}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 15}" in names

    def test_binary_literal_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${0b1010}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 10}" in names

    def test_number_no_diagnostic_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${1}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) == 0

    def test_scientific_notation_in_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${1e3}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1000.0}" in names

    def test_number_in_keyword_var_statement(self) -> None:
        result = _run_analyzer(
            """\
*** Keywords ***
My Keyword
    VAR    ${NESTED ${1}}    value
"""
        )
        names = _var_names(result)
        assert "${NESTED 1}" in names


# ──────────────────────────────────────────────────────────────────────
#  Number literal parity tests — *** Variables *** section
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="Nested variable names require RF >= 7.0")
class TestVariablesSectionNumberLiteralParity:
    """Both analyzers must produce identical results for number literals in nested names."""

    def test_integer_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${1}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_float_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${3.14}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_hex_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${0xFF}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_binary_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${0b1010}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_octal_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${0o17}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_negative_integer_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${-42}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_scientific_notation_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${1e3}}    value
"""
        )
        _assert_nested_var_parity(s, n)


# ──────────────────────────────────────────────────────────────────────
#  Number literal parity tests — VAR statements
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="VAR statements require RF >= 7.0")
class TestVarStatementNumberLiteralParity:
    """Both analyzers must produce identical results for number literals in VAR statements."""

    def test_integer_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${1}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_float_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${3.14}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_hex_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${0xFF}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_binary_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${0b1010}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_octal_literal_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${0o17}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_negative_integer_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${-42}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_scientific_notation_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${1e3}}    value
"""
        )
        _assert_nested_var_parity(s, n)


# ──────────────────────────────────────────────────────────────────────
#  Extended variable syntax — HINT instead of ERROR
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="Nested variable names require RF >= 7.0")
class TestVariablesSectionExtendedSyntax:
    """Extended variable syntax (${VAR.attr}, ${1-2}, ${LIST[0]}) in *** Variables *** section.

    These are potentially resolvable at runtime via RF's ExtendedFinder,
    so they should produce a HINT, not an ERROR.
    """

    def test_number_subtraction_is_hint(self) -> None:
        """${1-2} → base '1' is a number, extended '-2' is evaluable at runtime."""
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${1-2}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_dict_attribute_access_is_hint(self) -> None:
        """${A DICT.a} → base 'A DICT' exists, '.a' is attribute access."""
        result = _run_analyzer(
            """\
*** Variables ***
&{A DICT}    a=1    b=2
${NESTED ${A DICT.a}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_list_index_access_is_hint(self) -> None:
        """${A LIST[0]} → base 'A LIST' exists, '[0]' is index access."""
        result = _run_analyzer(
            """\
*** Variables ***
@{A LIST}    x    y    z
${NESTED ${A LIST[0]}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_unknown_base_is_error(self) -> None:
        """${UNKNOWN.a} → base 'UNKNOWN' not defined → ERROR, not HINT."""
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${UNKNOWN.a}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        assert len(errors) >= 1

    def test_number_with_attribute_is_hint(self) -> None:
        """${1.q} → base '1' is a number, '.q' is attribute → HINT (may fail at runtime)."""
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${1.q}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_scalar_base_with_method_call_is_hint(self) -> None:
        """${MYVAR.upper()} → base 'MYVAR' exists, '.upper()' is method call."""
        result = _run_analyzer(
            """\
*** Variables ***
${MYVAR}    hello
${NESTED ${MYVAR.upper()}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_number_addition_is_hint(self) -> None:
        """${1+2} → base '1' is a number, '+2' is evaluable."""
        result = _run_analyzer(
            """\
*** Variables ***
${NESTED ${1+2}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="Nested variable names require RF >= 7.0")
class TestVarStatementExtendedSyntax:
    """Extended variable syntax in VAR statements within *** Test Cases ***."""

    def test_number_subtraction_is_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${1-2}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_dict_attribute_access_is_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
&{A DICT}    a=1    b=2

*** Test Cases ***
Example
    VAR    ${NESTED ${A DICT.a}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_list_index_access_is_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
@{A LIST}    x    y    z

*** Test Cases ***
Example
    VAR    ${NESTED ${A LIST[0]}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_unknown_base_is_error(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${UNKNOWN.a}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        assert len(errors) >= 1

    def test_number_with_attribute_is_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${1.q}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_scalar_base_with_method_call_is_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${MYVAR}    hello

*** Test Cases ***
Example
    VAR    ${NESTED ${MYVAR.upper()}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1

    def test_number_addition_is_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${1+2}}    value
"""
        )
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        assert len(errors) == 0
        assert len(hints) >= 1


@pytest.mark.skipif(RF_VERSION < (7, 0), reason="Nested variable names require RF >= 7.0")
class TestExtendedSyntaxParity:
    """Both analyzers must produce identical results for extended variable syntax."""

    def test_number_subtraction_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${1-2}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_dict_attribute_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
&{A DICT}    a=1    b=2
${NESTED ${A DICT.a}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_list_index_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
@{A LIST}    x    y    z
${NESTED ${A LIST[0]}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_unknown_base_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${UNKNOWN.a}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_number_with_attribute_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${1.q}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_scalar_base_method_call_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${MYVAR}    hello
${NESTED ${MYVAR.upper()}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_number_addition_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
${NESTED ${1+2}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_var_statement_dict_attr_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
&{A DICT}    a=1    b=2

*** Test Cases ***
Example
    VAR    ${NESTED ${A DICT.a}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_var_statement_list_index_parity(self) -> None:
        s, n = _run_both(
            """\
*** Variables ***
@{A LIST}    x    y    z

*** Test Cases ***
Example
    VAR    ${NESTED ${A LIST[0]}}    value
"""
        )
        _assert_nested_var_parity(s, n)

    def test_var_statement_unknown_base_parity(self) -> None:
        s, n = _run_both(
            """\
*** Test Cases ***
Example
    VAR    ${NESTED ${UNKNOWN.a}}    value
"""
        )
        _assert_nested_var_parity(s, n)


@pytest.mark.skipif(RF_VERSION < (7, 3), reason="Variable type conversion requires RF >= 7.3")
class TestTypeHintedNestedDeclarationResolution:
    """Typed nested variable references in declaration contexts must resolve correctly."""

    def test_variables_section_nested_typed_reference_resolves(self) -> None:
        result = _run_analyzer(
            """\
*** Variables ***
${A}    1
${NESTED ${A}: int}    value
"""
        )

        names = _var_names(result)
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)

        assert "${A}" in names
        assert "${NESTED 1}" in names
        assert len(errors) == 0

    def test_var_statement_typed_nested_name_reports_static_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${A}    1
    VAR    ${NESTED ${A}: int}    value
"""
        )

        names = _var_names(result)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)

        assert "${A}" in names
        assert len(hints) == 1
        assert len(errors) == 0

    def test_assignment_typed_nested_name_reports_static_hint(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    ${A}    Evaluate    1
    ${NESTED ${A}: int}    Evaluate    2
"""
        )

        names = _var_names(result)
        hints = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE)
        errors = _diagnostics_with_code(result, Error.VARIABLE_NAME_NOT_RESOLVABLE)

        assert "${A}" in names
        assert len(hints) == 1
        assert len(errors) == 0

    def test_typed_reference_is_not_normalized_in_usage_context(self) -> None:
        result = _run_analyzer(
            """\
*** Test Cases ***
Example
    VAR    ${i: int}    1
    Log    ${i: int}
"""
        )

        names = _var_names(result)
        errors = _diagnostics_with_code(result, Error.VARIABLE_NOT_FOUND)

        assert "${i}" in names
        assert len(errors) == 1
