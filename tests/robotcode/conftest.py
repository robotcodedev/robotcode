"""Shared fixtures for the robotcode test suite.

Fixtures defined here are available to ALL tests under `tests/robotcode/*`
through pytest's conftest.py inheritance. Sub-directories (e.g.
`test_semantic_analyzer/`, `language_server/robotframework/parts/`) can
extend this with their own conftest.py files for module-specific setup.

The fixtures here cover the most common SemanticAnalyzer test setup so
that individual test files don't need to re-implement parsing, finder
mocks, or analyzer bootstrapping.
"""

import io
from ast import AST
from typing import Any, Callable, Optional

import pytest
from pytest_mock import MockerFixture
from robot.api import get_model

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.import_resolver import ResolvedImports
from robotcode.robot.diagnostics.keyword_finder import KeywordFinder
from robotcode.robot.diagnostics.library_doc import KeywordDoc, ResourceDoc
from robotcode.robot.diagnostics.semantic_analyzer.analyzer import (
    SemanticAnalyzer,
    _get_builtin_variables,
)
from robotcode.robot.diagnostics.variable_scope import VariableScope

# --------------------------------------------------------------------------
# Plain factories (no mocks, no fixtures needed — re-exported for
# convenience). Importable from tests under any sub-directory.
# --------------------------------------------------------------------------


def parse_robot(text: str) -> AST:
    """Parse Robot Framework text into an AST model."""
    return get_model(io.StringIO(text))  # type: ignore[no-any-return]


def make_resource_doc(source: str = "/test.robot") -> ResourceDoc:
    """Build a minimal ResourceDoc for analyzer setup."""
    return ResourceDoc(name="test", source=source)


# --------------------------------------------------------------------------
# Mock-builder fixtures (`mocker` is a pytest-mock fixture).
# --------------------------------------------------------------------------


@pytest.fixture
def make_finder(mocker: MockerFixture) -> Callable[..., KeywordFinder]:
    """Factory: build a `KeywordFinder` mock that resolves names from an
    optional `keyword_map` (`name -> KeywordDoc | None`).

    The mock uses `mocker.create_autospec` so it validates against the real
    interface. By default it returns `None` for any lookup.

    Examples:
        finder = make_finder()                              # always None
        finder = make_finder({"My Keyword": kw_doc})        # resolves My Keyword
    """

    def factory(keyword_map: Optional[dict[str, Optional[KeywordDoc]]] = None) -> KeywordFinder:
        finder = mocker.create_autospec(KeywordFinder, instance=True)
        finder.result_bdd_prefix = None
        finder.multiple_keywords_result = None
        finder.diagnostics = []

        kw_map = keyword_map or {}

        def find_keyword(name: str, raise_keyword_error: bool = True) -> Optional[KeywordDoc]:
            return kw_map.get(name)

        finder.find_keyword.side_effect = find_keyword
        return finder

    return factory


@pytest.fixture
def analyzer_factory(
    mocker: MockerFixture,
    make_finder: Callable[..., KeywordFinder],
) -> Callable[..., AnalyzerResult]:
    """Factory: parse text, set up a SemanticAnalyzer with the supplied
    keyword map, run it, and return the AnalyzerResult.

    Bypasses `analyzer.resolve()` (no real ImportsManager needed) by setting
    the relevant internal state directly. Use this fixture for the common
    "run the analyzer on this text and inspect the result" case; for more
    elaborate setup (e.g. pre-resolved imports with errors), build the
    analyzer manually using `parse_robot` + `make_resource_doc`.

    Examples:
        result = analyzer_factory("*** Test Cases ***\\nT\\n    Log    hi\\n")
        result = analyzer_factory(text, keyword_map={"My KW": kw_doc})
    """

    def factory(
        text: str,
        keyword_map: Optional[dict[str, Optional[KeywordDoc]]] = None,
        source: str = "/test.robot",
        library_doc: Optional[Any] = None,
    ) -> AnalyzerResult:
        model = parse_robot(text)
        analyzer = SemanticAnalyzer(model, source, f"file://{source}")

        if library_doc is None:
            analyzer._library_doc = make_resource_doc(source)
        else:
            analyzer._library_doc = library_doc

        analyzer._variable_scope = VariableScope(
            command_line=[],
            own=[],
            builtin=_get_builtin_variables(),
        )
        analyzer._resolved_imports = ResolvedImports()

        finder = make_finder(keyword_map)
        return analyzer.run(finder)

    return factory


@pytest.fixture
def make_library_doc_mock(mocker: MockerFixture) -> Callable[..., Any]:
    """Factory: build a `_library_doc`-shaped mock with `resource_variables`
    / `resource_imports` accessors. Useful when a real `ResourceDoc` would
    be over-the-top.
    """

    def factory(
        resource_variables: Optional[list[Any]] = None,
        resource_imports: Optional[list[Any]] = None,
    ) -> Any:
        doc = mocker.MagicMock()
        doc.resource_variables = resource_variables or []
        doc.resource_imports = resource_imports or []
        return doc

    return factory
