"""Tests for the environment variable diagnostics of both analyzers.

Robot Framework resolves `%{NAME=default}` to the default when `NAME` is not set, and an empty
default (`%{NAME=}`) is a default like any other: it resolves to an empty string.

Variables nested in the name or the default are resolved before the lookup, so an undefined one
fails even when `NAME` is set. An escaped `\\${var}` is not a variable.
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
OTHER_ENV_NAME = "ROBOTCODE_TEST_OTHER_ENV_VAR"

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


def _variable_diagnostics(result: AnalyzerResult) -> List[Diagnostic]:
    return [d for d in result.diagnostics if d.code in (Error.VARIABLE_NOT_FOUND, Error.VARIABLE_NOT_REPLACED)]


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


@pytest.mark.parametrize(
    ("var", "env_set"),
    [
        (f"%{{{ENV_NAME}_${{UNDEF}}}}", False),
        (f"%{{{ENV_NAME}_${{UNDEF}}=}}", False),
        (f"%{{{ENV_NAME}_${{UNDEF}}=abc}}", False),
        (f"%{{{ENV_NAME}=${{UNDEF}}}}", False),
        (f"%{{{ENV_NAME}=${{UNDEF}}}}", True),
        (f"%{{{ENV_NAME}=%{{{OTHER_ENV_NAME}=${{UNDEF}}}}}}", False),
        (f"%{{{ENV_NAME}=%{{{OTHER_ENV_NAME}=${{UNDEF}}}}}}", True),
    ],
    ids=[
        "in name",
        "in name with empty default",
        "in name with default",
        "in default",
        "in default of set variable",
        "in nested default",
        "in nested default of set variable",
    ],
)
def test_undefined_variable_nested_in_environment_variable_is_reported(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch, var: str, env_set: bool
) -> None:
    if env_set:
        monkeypatch.setenv(ENV_NAME, "value")
    else:
        monkeypatch.delenv(ENV_NAME, raising=False)
    monkeypatch.delenv(OTHER_ENV_NAME, raising=False)
    offset = var.index("${UNDEF}") + 2

    diagnostics = _variable_diagnostics(analyze(SUITE.format(var=var)))

    assert [d.range.start for d in diagnostics] == [
        Position(line=1, character=12 + offset),
        Position(line=2, character=17 + offset),
        Position(line=6, character=11 + offset),
    ]
    assert {d.code for d in diagnostics} == {Error.VARIABLE_NOT_FOUND}
    assert {d.message for d in diagnostics} == {"Variable '${UNDEF}' not found."}


@pytest.mark.parametrize("env_set", [False, True], ids=["unset", "set"])
def test_unset_environment_variable_nested_in_default_is_reported(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch, env_set: bool
) -> None:
    if env_set:
        monkeypatch.setenv(ENV_NAME, "value")
    else:
        monkeypatch.delenv(ENV_NAME, raising=False)
    monkeypatch.delenv(OTHER_ENV_NAME, raising=False)
    var = f"%{{{ENV_NAME}=%{{{OTHER_ENV_NAME}}}}}"
    offset = var.index(OTHER_ENV_NAME)

    diagnostics = _env_diagnostics(analyze(SUITE.format(var=var)))

    assert [d.range.start for d in diagnostics] == [
        Position(line=1, character=12 + offset),
        Position(line=2, character=17 + offset),
        Position(line=6, character=11 + offset),
    ]
    assert {d.code for d in diagnostics} == {Error.ENVIRONMENT_VARIABLE_NOT_FOUND}
    assert {d.message for d in diagnostics} == {f"Environment variable '%{{{OTHER_ENV_NAME}}}' not found."}


@pytest.mark.parametrize(
    "var",
    [f"%{{{ENV_NAME}=\\${{UNDEF}}}}", f"%{{{ENV_NAME}_\\${{UNDEF}}=abc}}", f"%{{{ENV_NAME}=%{{{OTHER_ENV_NAME}=}}}}"],
    ids=["escaped in default", "escaped in name", "nested with default"],
)
def test_resolvable_environment_variable_with_nested_syntax_is_not_reported(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch, var: str
) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)
    monkeypatch.delenv(OTHER_ENV_NAME, raising=False)

    result = analyze(SUITE.format(var=var))

    assert _variable_diagnostics(result) == []
    assert _env_diagnostics(result) == []


def test_variables_nested_in_environment_variable_are_referenced(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)
    in_name = f"%{{{ENV_NAME}_${{IN_NAME}}=abc}}"
    in_default = f"%{{{ENV_NAME}=${{IN_DEFAULT}}}}"

    result = analyze(
        f"*** Variables ***\n${{IN_NAME}}    x\n${{IN_DEFAULT}}    y\n\n"
        f"*** Test Cases ***\nTest\n    Log    {in_name}\n    Log    {in_default}\n"
    )

    assert _variable_diagnostics(result) == []
    assert _env_diagnostics(result) == []
    references = {
        var.name: [(loc.range.start.line, loc.range.start.character) for loc in locations]
        for var, locations in result.variable_references.items()
        if var.name in ("${IN_NAME}", "${IN_DEFAULT}")
    }
    assert references == {
        "${IN_NAME}": [(6, 11 + in_name.index("IN_NAME"))],
        "${IN_DEFAULT}": [(7, 11 + in_default.index("IN_DEFAULT"))],
    }


def test_undefined_variable_nested_in_environment_variable_in_documentation_is_not_replaced(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)
    var = f"%{{{ENV_NAME}=${{UNDEF}}}}"

    diagnostics = _variable_diagnostics(
        analyze(f"*** Test Cases ***\nTest\n    [Documentation]    doc {var}\n    Log    x\n")
    )

    assert [d.range.start for d in diagnostics] == [Position(line=2, character=27 + var.index("UNDEF"))]
    assert {d.code for d in diagnostics} == {Error.VARIABLE_NOT_REPLACED}
    assert {d.message for d in diagnostics} == {"Variable '${UNDEF}' not replaced."}


# In the following cases the NamespaceAnalyzer also reports the outer environment variable,
# which Robot Framework does not, so they only run the SemanticAnalyzer.


def test_environment_variable_with_undefined_variable_in_name_is_not_reported(
    analyzer_factory: Callable[..., AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)

    assert _env_diagnostics(analyzer_factory(SUITE.format(var=f"%{{{ENV_NAME}_${{UNDEF}}}}"))) == []


def test_environment_variable_named_by_set_environment_variable_is_not_reported(
    analyzer_factory: Callable[..., AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(OTHER_ENV_NAME, ENV_NAME)
    monkeypatch.setenv(ENV_NAME, "value")

    assert _env_diagnostics(analyzer_factory(SUITE.format(var=f"%{{%{{{OTHER_ENV_NAME}}}}}"))) == []


def test_environment_variable_named_by_unset_environment_variable_reports_only_the_nested_one(
    analyzer_factory: Callable[..., AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(OTHER_ENV_NAME, raising=False)

    diagnostics = _env_diagnostics(analyzer_factory(SUITE.format(var=f"%{{%{{{OTHER_ENV_NAME}}}}}")))

    assert [d.range.start for d in diagnostics] == [
        Position(line=1, character=16),
        Position(line=2, character=21),
        Position(line=6, character=15),
    ]
    assert {d.message for d in diagnostics} == {f"Environment variable '%{{{OTHER_ENV_NAME}}}' not found."}


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
