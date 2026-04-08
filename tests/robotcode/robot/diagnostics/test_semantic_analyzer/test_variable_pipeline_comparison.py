"""Transitional comparison tests for variable analysis pipeline.

These tests intentionally compare SemanticAnalyzer against NamespaceAnalyzer.
They can be removed once the old analyzer is retired (Phase 4).
"""

import io
from ast import AST
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from robot.api import get_model
from robot.parsing.lexer.tokens import Token

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


def _var(name: str, source: str = "/test.robot") -> VariableDefinition:
    return VariableDefinition(
        line_no=1,
        col_offset=0,
        end_line_no=1,
        end_col_offset=len(name),
        source=source,
        name=name,
        name_token=None,
    )


def _prepare_analyzer(analyzer: SemanticAnalyzer | NamespaceAnalyzer, source: str) -> None:
    analyzer._library_doc = ResourceDoc(name="test", source=source)
    analyzer._variable_scope = VariableScope(
        command_line=[],
        own=[],
        builtin=_get_builtin_variables(),
    )
    analyzer._resolved_imports = ResolvedImports()

    vars_map = {
        _var("${name}").matcher: _var("${name}"),
        _var("${base}").matcher: _var("${base}"),
        _var("${idx}").matcher: _var("${idx}"),
        _var("%{HOME}").matcher: _var("%{HOME}"),
    }

    analyzer._variables = vars_map
    analyzer._suite_variables = vars_map.copy()
    analyzer._block_variables = None


def _collect(analyzer: SemanticAnalyzer | NamespaceAnalyzer, token: Token) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    for var_token, var_def in analyzer._iter_variables_from_token(token):
        result.append((var_token.value, var_def.name, var_def.type.value))
    return result


@pytest.mark.parametrize(
    ("value", "token_type"),
    [
        ("${name}", Token.ARGUMENT),
        ("${obj.attr}", Token.ARGUMENT),
        ("${name}[0]", Token.ARGUMENT),
        ("%{HOME=/tmp}", Token.ARGUMENT),
        ("${cfg_${idx}}", Token.ARGUMENT),
        ("${{$base + 1}}", Token.ARGUMENT),
        ("${name}=", Token.VARIABLE),
        ("prefix ${name} suffix", Token.ARGUMENT),
    ],
)
def test_semantic_and_namespace_variable_pipeline_match(value: str, token_type: str) -> None:
    source = "/test.robot"
    model = _parse("*** Test Cases ***\nT\n    No Operation")

    semantic = SemanticAnalyzer(model, source, f"file://{source}")
    namespace = NamespaceAnalyzer(model, source, f"file://{source}")

    _prepare_analyzer(semantic, source)
    _prepare_analyzer(namespace, source)

    token = Token(token_type, value, 3, 4)

    assert _collect(semantic, token) == _collect(namespace, token)


def _make_finder() -> KeywordFinder:
    finder = MagicMock(spec=KeywordFinder)
    finder.find_keyword.return_value = None
    finder.result_bdd_prefix = None
    finder.multiple_keywords_result = None
    finder.diagnostics = []
    return finder


def _run_with_bypass(analyzer: SemanticAnalyzer | NamespaceAnalyzer, source: str, text: str) -> Any:
    analyzer._model = _parse(text)
    _prepare_analyzer(analyzer, source)
    return analyzer.run(_make_finder())


def _diag_signature(result: Any) -> list[tuple[int, int, int, int, str, Any, Any]]:
    variable_codes = {
        Error.VARIABLE_NOT_FOUND,
        Error.VARIABLE_NOT_REPLACED,
        Error.ENVIRONMENT_VARIABLE_NOT_FOUND,
        Error.ENVIRONMENT_VARIABLE_NOT_REPLACED,
    }
    return sorted(
        [
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
            if d.code in variable_codes
        ]
    )


def _var_refs_signature(result: Any) -> list[tuple[str, str, tuple[tuple[int, int, int, int], ...]]]:
    items: list[tuple[str, str, tuple[tuple[int, int, int, int], ...]]] = []
    for var_def, locations in result.variable_references.items():
        loc_sig = tuple(
            sorted(
                (
                    loc.range.start.line,
                    loc.range.start.character,
                    loc.range.end.line,
                    loc.range.end.character,
                )
                for loc in locations
            )
        )
        items.append((var_def.name, var_def.type.value, loc_sig))
    return sorted(items)


def test_semantic_and_namespace_run_parity_for_variable_diagnostics_and_refs() -> None:
    source = "/test.robot"
    text = """*** Test Cases ***
T
    Log    ${name}
    Log    ${obj.attr}
    Log    ${missing}
    Log    ${cfg_${idx}}
    Log    ${{$base + $missing_inner}}
"""

    semantic = SemanticAnalyzer(_parse(text), source, f"file://{source}")
    namespace = NamespaceAnalyzer(_parse(text), source, f"file://{source}")

    semantic_result = _run_with_bypass(semantic, source, text)
    namespace_result = _run_with_bypass(namespace, source, text)

    assert _diag_signature(semantic_result) == _diag_signature(namespace_result)
    assert _var_refs_signature(semantic_result) == _var_refs_signature(namespace_result)


# --- Comprehensive Parity Tests (all AnalyzerResult fields) ---


def _all_diag_signature(result: Any) -> list[tuple[int, int, int, int, str, Any, Any]]:
    """Signature for ALL diagnostics, not just variable-related ones."""
    return sorted(
        [
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
        ]
    )


def _kw_refs_signature(result: Any) -> list[tuple[str, tuple[tuple[int, int, int, int], ...]]]:
    items: list[tuple[str, tuple[tuple[int, int, int, int], ...]]] = []
    for kw_doc, locations in result.keyword_references.items():
        loc_sig = tuple(
            sorted(
                (
                    loc.range.start.line,
                    loc.range.start.character,
                    loc.range.end.line,
                    loc.range.end.character,
                )
                for loc in locations
            )
        )
        items.append((kw_doc.name, loc_sig))
    return sorted(items)


def _local_var_assign_signature(
    result: Any,
) -> list[tuple[str, str, tuple[tuple[int, int, int, int], ...]]]:
    items: list[tuple[str, str, tuple[tuple[int, int, int, int], ...]]] = []
    for var_def, ranges in result.local_variable_assignments.items():
        range_sig = tuple(
            sorted(
                (
                    r.start.line,
                    r.start.character,
                    r.end.line,
                    r.end.character,
                )
                for r in ranges
            )
        )
        items.append((var_def.name, var_def.type.value, range_sig))
    return sorted(items)


def _ns_refs_signature(result: Any) -> list[tuple[str, tuple[tuple[int, int, int, int], ...]]]:
    items: list[tuple[str, tuple[tuple[int, int, int, int], ...]]] = []
    for entry, locations in result.namespace_references.items():
        loc_sig = tuple(
            sorted(
                (
                    loc.range.start.line,
                    loc.range.start.character,
                    loc.range.end.line,
                    loc.range.end.character,
                )
                for loc in locations
            )
        )
        items.append((entry.name, loc_sig))
    return sorted(items)


def _test_case_defs_signature(result: Any) -> list[tuple[str, int, int, int, int]]:
    return sorted(
        [(tc.name, tc.line_no, tc.col_offset, tc.end_line_no, tc.end_col_offset) for tc in result.test_case_definitions]
    )


def _tag_refs_signature(refs: Any) -> list[tuple[str, tuple[tuple[int, int, int, int], ...]]]:
    items: list[tuple[str, tuple[tuple[int, int, int, int], ...]]] = []
    for tag, locations in refs.items():
        loc_sig = tuple(
            sorted(
                (
                    loc.range.start.line,
                    loc.range.start.character,
                    loc.range.end.line,
                    loc.range.end.character,
                )
                for loc in locations
            )
        )
        items.append((tag, loc_sig))
    return sorted(items)


def _scope_tree_signature(result: Any) -> list[tuple[str, int, int, int, int, int]]:
    """Extract LocalScope data for comparison."""
    scopes = result.scope_tree.local_scopes
    items: list[tuple[str, int, int, int, int, int]] = []
    for scope in scopes:
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


def _assert_full_parity(semantic_result: Any, namespace_result: Any) -> None:
    """Assert all AnalyzerResult fields match between both analyzers."""
    assert _all_diag_signature(semantic_result) == _all_diag_signature(namespace_result), "diagnostics mismatch"
    assert _kw_refs_signature(semantic_result) == _kw_refs_signature(namespace_result), "keyword_references mismatch"
    assert _var_refs_signature(semantic_result) == _var_refs_signature(namespace_result), "variable_references mismatch"
    assert _local_var_assign_signature(semantic_result) == _local_var_assign_signature(namespace_result), (
        "local_variable_assignments mismatch"
    )
    assert _ns_refs_signature(semantic_result) == _ns_refs_signature(namespace_result), "namespace_references mismatch"
    assert _test_case_defs_signature(semantic_result) == _test_case_defs_signature(namespace_result), (
        "test_case_definitions mismatch"
    )
    assert _tag_refs_signature(semantic_result.keyword_tag_references) == _tag_refs_signature(
        namespace_result.keyword_tag_references
    ), "keyword_tag_references mismatch"
    assert _tag_refs_signature(semantic_result.testcase_tag_references) == _tag_refs_signature(
        namespace_result.testcase_tag_references
    ), "testcase_tag_references mismatch"
    assert _tag_refs_signature(semantic_result.metadata_references) == _tag_refs_signature(
        namespace_result.metadata_references
    ), "metadata_references mismatch"
    assert _scope_tree_signature(semantic_result) == _scope_tree_signature(namespace_result), "scope_tree mismatch"


_PARITY_CASES: dict[str, str] = {
    "simple_keyword_calls": """\
*** Test Cases ***
Simple Test
    Log    Hello World
    Log    ${name}
    Log    ${missing}
""",
    "multiple_test_cases": """\
*** Test Cases ***
First Test
    No Operation

Second Test
    Log    message
""",
    "keyword_definition": """\
*** Test Cases ***
Test Using Keyword
    My Custom Keyword    arg1

*** Keywords ***
My Custom Keyword
    [Arguments]    ${arg}
    Log    ${arg}
""",
    "variable_assignments": """\
*** Test Cases ***
Assignment Test
    ${result}=    Set Variable    hello
    Log    ${result}
""",
    "for_loop": """\
*** Test Cases ***
For Test
    FOR    ${item}    IN    a    b    c
        Log    ${item}
    END
""",
    "if_else": """\
*** Test Cases ***
If Test
    IF    True
        Log    yes
    ELSE
        Log    no
    END
""",
    "try_except": """\
*** Test Cases ***
Try Test
    TRY
        Log    trying
    EXCEPT    message
        Log    caught
    FINALLY
        Log    done
    END
""",
    "tags": """\
*** Test Cases ***
Tagged Test
    [Tags]    smoke    regression
    No Operation
""",
    "variables_section": """\
*** Variables ***
${SCALAR}    value
@{LIST}      a    b    c

*** Test Cases ***
Var Test
    Log    ${SCALAR}
    Log    @{LIST}
""",
    "keyword_with_args_and_return": """\
*** Keywords ***
Compute
    [Arguments]    ${a}    ${b}
    ${sum}=    Evaluate    ${a} + ${b}
    RETURN    ${sum}
""",
    "template": """\
*** Test Cases ***
Template Test
    [Template]    Log
    Hello
    World
""",
    "setup_teardown": """\
*** Test Cases ***
Setup Test
    [Setup]    Log    setup
    [Teardown]    Log    teardown
    No Operation
""",
    "comments": """\
*** Comments ***
This is a comment block.

*** Test Cases ***
Test
    # inline comment
    No Operation
""",
    "while_loop": """\
*** Test Cases ***
While Test
    WHILE    True    limit=3
        Log    looping
    END
""",
    "nested_control": """\
*** Test Cases ***
Nested Test
    FOR    ${i}    IN RANGE    3
        IF    True
            Log    ${i}
        END
    END
""",
    "multiple_keywords": """\
*** Keywords ***
First KW
    [Arguments]    ${x}
    Log    ${x}

Second KW
    [Tags]    helper
    First KW    hello
""",
}


@pytest.mark.parametrize("case_name", list(_PARITY_CASES.keys()))
def test_full_analyzer_parity(case_name: str) -> None:
    """Compare ALL AnalyzerResult fields between SemanticAnalyzer and NamespaceAnalyzer."""
    source = "/test.robot"
    text = _PARITY_CASES[case_name]

    semantic = SemanticAnalyzer(_parse(text), source, f"file://{source}")
    namespace = NamespaceAnalyzer(_parse(text), source, f"file://{source}")

    semantic_result = _run_with_bypass(semantic, source, text)
    namespace_result = _run_with_bypass(namespace, source, text)

    _assert_full_parity(semantic_result, namespace_result)


# --- Parity tests using real .robot files from LSP test data ---

_LSP_DATA_PATH = Path(__file__).resolve().parents[3] / "language_server" / "robotframework" / "parts" / "data"
_LSP_ROBOT_FILES = sorted(_LSP_DATA_PATH.rglob("*.robot")) if _LSP_DATA_PATH.exists() else []

# Known parity differences between SemanticAnalyzer and NamespaceAnalyzer.
# In both cases below the SemanticAnalyzer is *more correct* than the
# NamespaceAnalyzer; the xfail markers keep the suite green while the
# old analyzer is still in place.
_XFAIL_FILES: dict[str, str] = {
    "tests/variables.robot": "SemanticAnalyzer correctly omits spurious ${%%} diagnostics for %%{ENV} vars",
}

# RF < 7 doesn't resolve variables inside variable names at runtime,
# so the NamespaceAnalyzer still tracks a spurious reference for
# ${INVALID VAR ${}} while the SemanticAnalyzer correctly skips it.
if RF_VERSION < (7, 0):
    _XFAIL_FILES["tests/hover.robot"] = (
        "SemanticAnalyzer correctly skips reference to invalid ${INVALID VAR ${}} (RF < 7)"
    )


def _run_file_with_bypass(analyzer: SemanticAnalyzer | NamespaceAnalyzer, path: Path) -> Any:
    source = str(path)
    model = get_model(source)
    analyzer._model = model
    _prepare_analyzer(analyzer, source)
    return analyzer.run(_make_finder())


@pytest.mark.parametrize(
    "robot_file",
    _LSP_ROBOT_FILES,
    ids=[str(f.relative_to(_LSP_DATA_PATH)) for f in _LSP_ROBOT_FILES],
)
def test_full_analyzer_parity_on_lsp_data(robot_file: Path) -> None:
    """Run both analyzers on real .robot files from the LSP test suite and compare all outputs."""
    rel = str(robot_file.relative_to(_LSP_DATA_PATH))
    if rel in _XFAIL_FILES:
        pytest.xfail(_XFAIL_FILES[rel])

    source = str(robot_file)
    model = get_model(source)

    semantic = SemanticAnalyzer(model, source, f"file://{source}")
    namespace = NamespaceAnalyzer(model, source, f"file://{source}")

    semantic_result = _run_file_with_bypass(semantic, robot_file)
    namespace_result = _run_file_with_bypass(namespace, robot_file)

    _assert_full_parity(semantic_result, namespace_result)
