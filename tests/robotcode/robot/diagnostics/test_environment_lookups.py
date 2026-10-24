"""Tests for the environment variables both analyzers record for the namespace cache.

The namespace cache compares them with the environment when it restores an analysis: for each variable the analysis
checked without a default value whether it is set, and for each variable whose value it used the hash of the value.
"""

from typing import Callable, Optional

import pytest

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.namespace_analyzer import NamespaceAnalyzer
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import _get_builtin_variables
from robotcode.robot.diagnostics.variable_scope import VariableScope
from robotcode.robot.utils import RF_VERSION
from robotcode.robot.utils.variables import environment_value_hash
from tests.robotcode.conftest import make_resource_doc, parse_robot

SOURCE = "/test.robot"
ENV_NAME = "ROBOTCODE_TEST_ENV_VAR"
OTHER_ENV_NAME = "ROBOTCODE_TEST_OTHER_ENV_VAR"

nested_names = pytest.mark.skipif(RF_VERSION < (7, 0), reason="variables in variable names exist from RF 7.0 on")


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


def _test(*lines: str) -> str:
    return "*** Test Cases ***\nTest\n" + "".join(f"    {line}\n" for line in lines)


@pytest.mark.parametrize("value", ["x", None], ids=["set", "unset"])
def test_a_variable_without_default_is_recorded_as_set_or_not(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch, value: Optional[str]
) -> None:
    if value is None:
        monkeypatch.delenv(ENV_NAME, raising=False)
    else:
        monkeypatch.setenv(ENV_NAME, value)

    result = analyze(_test(f"Log    %{{{ENV_NAME}}}"))

    assert result.environment_set == {ENV_NAME: value is not None}
    assert result.environment_values == {}


def test_a_variable_with_default_is_not_recorded(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(ENV_NAME, raising=False)

    result = analyze(_test(f"Log    %{{{ENV_NAME}=x}}"))

    assert result.environment_set == {}
    assert result.environment_values == {}


@nested_names
def test_the_value_of_a_variable_in_a_variable_name_is_recorded_as_hash(
    analyze: Callable[[str], AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_NAME, "a")

    result = analyze(_test(f"VAR    ${{NAME_%{{{ENV_NAME}}}}}    value", "Log    ${NAME_a}"))

    assert result.environment_values == {ENV_NAME: environment_value_hash("a")}


# only the SemanticAnalyzer resolves the name; the NamespaceAnalyzer checks it as written
@nested_names
def test_the_value_of_a_variable_that_names_another_one_is_recorded_as_hash(
    analyzer_factory: Callable[..., AnalyzerResult], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_NAME, OTHER_ENV_NAME)
    monkeypatch.setenv(OTHER_ENV_NAME, "y")

    result = analyzer_factory(_test(f"Log    %{{%{{{ENV_NAME}}}}}"))

    assert result.environment_values.get(ENV_NAME) == environment_value_hash(OTHER_ENV_NAME)
