"""Level C snapshot tests for SemanticAnalyzer output.

These tests serialize the analyzer result into deterministic YAML and guard
against structural regressions in statements, diagnostics, and references.
"""

import io
from ast import AST
from typing import Any, Dict, List, cast
from unittest.mock import MagicMock

import pytest
import yaml
from robot.api import get_model

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.library_doc import ResourceDoc
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import SemanticAnalyzer, _get_builtin_variables
from robotcode.robot.diagnostics.semantic_analyzer.nodes import DefinitionStatement
from robotcode.robot.diagnostics.variable_scope import VariableScope


def _parse(text: str) -> AST:
    return get_model(io.StringIO(text))  # type: ignore[no-any-return]


def _make_finder() -> KeywordFinder:
    finder = MagicMock(spec=KeywordFinder)
    finder.find_keyword.return_value = None
    finder.result_bdd_prefix = None
    finder.multiple_keywords_result = None
    finder.diagnostics = []
    return finder


def _run_analyzer(text: str, source: str = "/test.robot") -> AnalyzerResult:
    model = _parse(text)
    analyzer = SemanticAnalyzer(model, source, f"file://{source}")

    analyzer._library_doc = ResourceDoc(name="test", source=source)
    analyzer._variable_scope = VariableScope(
        command_line=[],
        own=[],
        builtin=_get_builtin_variables(),
    )
    analyzer._resolved_imports = ResolvedImports()

    return analyzer.run(_make_finder())


def _diagnostic_sort_key(item: Dict[str, Any]) -> tuple[List[int], str]:
    range_info = cast(Dict[str, List[int]], item["range"])
    return (range_info["start"], cast(str, item["message"]))


def _serialize_result(result: AnalyzerResult) -> Dict[str, Any]:
    model = result.semantic_model
    assert model is not None

    statements: List[Dict[str, Any]] = []
    for stmt in model.statements:
        statements.append(
            {
                "type": stmt.__class__.__name__,
                "kind": stmt.kind.value,
                "line_start": stmt.line_start,
                "line_end": stmt.line_end,
                "name": getattr(stmt, "name", None),
                "setting_name": getattr(stmt, "setting_name", None),
                "import_type": getattr(getattr(stmt, "import_type", None), "value", None),
                "import_name": getattr(stmt, "import_name", None),
                "token_count": len(stmt.tokens),
            }
        )

    diagnostics = sorted(
        [
            {
                "message": d.message,
                "severity": int(d.severity) if d.severity is not None else None,
                "code": str(d.code) if d.code is not None else None,
                "range": {
                    "start": [d.range.start.line, d.range.start.character],
                    "end": [d.range.end.line, d.range.end.character],
                },
            }
            for d in result.diagnostics
        ],
        key=_diagnostic_sort_key,
    )

    variable_refs = sorted(
        [
            {
                "name": var.name,
                "type": var.type.value,
                "count": len(locations),
            }
            for var, locations in result.variable_references.items()
        ],
        key=lambda x: (x["name"], x["type"]),
    )

    return {
        "statement_count": len(statements),
        "statements": statements,
        "diagnostic_count": len(diagnostics),
        "diagnostics": diagnostics,
        "test_case_definitions": [d.name for d in result.test_case_definitions],
        "variable_references": variable_refs,
    }


def _statement_kind_sequence(result: AnalyzerResult) -> List[str]:
    model = result.semantic_model
    assert model is not None
    return [stmt.kind.value for stmt in model.statements]


def _definition_locals(result: AnalyzerResult) -> Dict[str, List[str]]:
    model = result.semantic_model
    assert model is not None

    output: Dict[str, List[str]] = {}
    for stmt in model.statements:
        if isinstance(stmt, DefinitionStatement) and stmt.name:
            output[stmt.name] = sorted(var.name for var, _ in stmt.local_variables)

    return output


def _variable_reference_names(result: AnalyzerResult) -> List[str]:
    return sorted({var.name for var in result.variable_references})


@pytest.mark.parametrize(
    ("text", "expected_kind_sequence", "expected_definition_locals", "expected_referenced_variables"),
    [
        (
            """\
*** Settings ***
Library    Collections

*** Test Cases ***
My Test
    [Tags]    smoke    regression
    ${x}=    Set Variable    hello
    FOR    ${item}    IN    a    b
        Log    ${item}
    END
""",
            [
                "unknown",
                "import",
                "unknown",
                "unknown",
                "test_case_def",
                "setting",
                "keyword_call",
                "for_header",
                "keyword_call",
                "unknown",
            ],
            {"My Test": ["${item}", "${x}"]},
            ["${item}", "${x}"],
        ),
        (
            """\
*** Keywords ***
My Keyword
    [Arguments]    ${name}
    IF    ${name}
        Log    ${name}
    END

*** Test Cases ***
Use Keyword
    My Keyword    world
""",
            [
                "unknown",
                "keyword_def",
                "setting",
                "if_header",
                "keyword_call",
                "unknown",
                "unknown",
                "unknown",
                "test_case_def",
                "keyword_call",
            ],
            {"My Keyword": ["${name}"], "Use Keyword": []},
            ["${name}"],
        ),
    ],
    ids=["settings_for_loop", "keyword_if_call"],
)
def test_semantic_analyzer_snapshot(
    regtest: Any,
    text: str,
    expected_kind_sequence: List[str],
    expected_definition_locals: Dict[str, List[str]],
    expected_referenced_variables: List[str],
) -> None:
    result = _run_analyzer(text)

    assert _statement_kind_sequence(result) == expected_kind_sequence
    assert _definition_locals(result) == expected_definition_locals

    referenced_variables = _variable_reference_names(result)
    for name in expected_referenced_variables:
        assert name in referenced_variables

    regtest.write(yaml.dump(_serialize_result(result), sort_keys=False))
