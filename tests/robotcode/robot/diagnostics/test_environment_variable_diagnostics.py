"""Tests for the environment variable diagnostics of both analyzers.

Robot Framework resolves `%{NAME=default}` to the default when `NAME` is not set, and an empty
default (`%{NAME=}`) is a default like any other: it resolves to an empty string.
"""

from typing import Callable, List, Optional

import pytest

from robotcode.core.lsp.types import Diagnostic, Position
from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.entities import EnvironmentVariableDefinition, VariableDefinition
from robotcode.robot.diagnostics.errors import Error
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.namespace_analyzer import NamespaceAnalyzer
from robotcode.robot.diagnostics.scope_tree import ScopeTree
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import SemanticAnalyzer, _get_builtin_variables
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.variable_scope import VariableScope
from tests.robotcode.conftest import make_resource_doc, parse_robot

SOURCE = "/test.robot"
ENV_NAME = "ROBOTCODE_TEST_ENV_VAR"

SUITE = """\
*** Variables ***
${{ALONE}}    {var}
${{EMBEDDED}}    x-{var}-y

*** Test Cases ***
Test
    Log    {var}
"""


@pytest.fixture(params=["SemanticAnalyzer", "NamespaceAnalyzer"])
def analyze(
    request: pytest.FixtureRequest,
    analyzer_factory: Callable[..., AnalyzerResult],
    make_finder: Callable[..., KeywordFinder],
) -> Callable[[str], AnalyzerResult]:
    if request.param == "SemanticAnalyzer":
        return analyzer_factory

    def factory(text: str) -> AnalyzerResult:
        analyzer = NamespaceAnalyzer(parse_robot(text), SOURCE, f"file://{SOURCE}")
        analyzer._library_doc = make_resource_doc(SOURCE)
        analyzer._variable_scope = VariableScope(command_line=[], own=[], builtin=_get_builtin_variables())
        analyzer._resolved_imports = ResolvedImports()
        return analyzer.run(make_finder())

    return factory


def _env_diagnostics(result: AnalyzerResult) -> List[Diagnostic]:
    return [
        d
        for d in result.diagnostics
        if d.code in (Error.ENVIRONMENT_VARIABLE_NOT_FOUND, Error.ENVIRONMENT_VARIABLE_NOT_REPLACED)
    ]


@pytest.mark.parametrize("var", [f"%{{{ENV_NAME}=}}", f"%{{{ENV_NAME}=abc}}"], ids=["empty default", "default"])
def test_unset_variable_with_default_is_not_reported(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch, var: str
) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)

    assert _env_diagnostics(analyze(SUITE.format(var=var))) == []


def test_unset_variable_without_default_is_reported(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)

    diagnostics = _env_diagnostics(analyze(SUITE.format(var=f"%{{{ENV_NAME}}}")))

    assert [d.range.start for d in diagnostics] == [
        Position(line=1, character=14),
        Position(line=2, character=19),
        Position(line=6, character=13),
    ]
    assert {d.code for d in diagnostics} == {Error.ENVIRONMENT_VARIABLE_NOT_FOUND}
    assert {d.message for d in diagnostics} == {f"Environment variable '%{{{ENV_NAME}}}' not found."}


def test_set_variable_without_default_is_not_reported(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_NAME, "value")

    assert _env_diagnostics(analyze(SUITE.format(var=f"%{{{ENV_NAME}}}"))) == []


def _namespace_analyzer_find(name: str) -> Optional[VariableDefinition]:
    return NamespaceAnalyzer(parse_robot(""), SOURCE, f"file://{SOURCE}")._find_variable(name)


def _semantic_analyzer_find(name: str) -> Optional[VariableDefinition]:
    return SemanticAnalyzer(parse_robot(""), SOURCE, f"file://{SOURCE}")._find_variable(name)


def _scope_tree_find(name: str) -> Optional[VariableDefinition]:
    return ScopeTree(VariableScope(), []).find_variable(name)


def _semantic_model_find(name: str) -> Optional[VariableDefinition]:
    return SemanticModel(statements=[]).find_variable(name, 1)


@pytest.mark.parametrize(
    "find_variable",
    [_namespace_analyzer_find, _semantic_analyzer_find, _scope_tree_find, _semantic_model_find],
    ids=["NamespaceAnalyzer", "SemanticAnalyzer", "ScopeTree", "SemanticModel"],
)
@pytest.mark.parametrize(
    ("name", "default_value"),
    [("%{NAME=}", ""), ("%{NAME=abc}", "abc"), ("%{NAME}", None)],
    ids=["empty default", "default", "no default"],
)
def test_environment_variable_definition_keeps_the_default(
    find_variable: Callable[[str], Optional[VariableDefinition]], name: str, default_value: Optional[str]
) -> None:
    var = find_variable(name)

    assert isinstance(var, EnvironmentVariableDefinition)
    assert var.name == "%{NAME}"
    assert var.default_value == default_value
