"""Tests for the diagnostic of a `Tags:` section without an empty row before it (Robot Framework 7.5)."""

from typing import Callable, List, Optional

import pytest

from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, DiagnosticTag, Position, Range
from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.diagnostic_rules import tags_line_without_empty_row
from robotcode.robot.diagnostics.diagnostics_modifier import DiagnosticsModifier
from robotcode.robot.diagnostics.errors import Error
from robotcode.robot.utils import RF_VERSION
from tests.robotcode.conftest import parse_robot

needs_rf_75 = pytest.mark.skipif(RF_VERSION < (7, 5), reason="Robot Framework warns about the layout since 7.5")


@pytest.mark.parametrize(
    ("doc", "expected"),
    [
        pytest.param("Does something.\nTags: a, b", 1, id="text then tags"),
        pytest.param("Does something.\n\nTags: a, b", None, id="empty line before"),
        pytest.param("Tags: a, b", None, id="first line"),
        pytest.param("Does something.\n\nArgs:\n    x: the x\nTags: a", None, id="after an args section"),
        pytest.param("We use\ntags: for grouping", 1, id="prose line"),
        pytest.param("Does something.\n**Tags:** a", 1, id="bold"),
        pytest.param("Does something.\n_Tags_: a", 1, id="italic"),
        pytest.param("Does something.\nTags:: a", 1, id="two colons"),
        pytest.param("Does something.\nArgs: x", None, id="other section header"),
        pytest.param("Does something.\nTagsx: a", None, id="not a header"),
    ],
)
def test_tags_line_without_empty_row(doc: str, expected: Optional[int]) -> None:
    assert tags_line_without_empty_row(doc) == expected


LEGACY_KEYWORD = """\
*** Keywords ***
Legacy Layout
    [Documentation]    Does something.
    ...    Tags: a, b
    No Operation
"""


def _tags_diagnostics(result: AnalyzerResult) -> List[Diagnostic]:
    return [d for d in result.diagnostics if d.code == Error.TAGS_WITHOUT_EMPTY_ROW]


@needs_rf_75
@pytest.mark.parametrize("source", ["/keywords.resource", "/suite.robot"])
def test_legacy_layout_is_reported(analyzer_factory: Callable[..., AnalyzerResult], source: str) -> None:
    diagnostics = _tags_diagnostics(analyzer_factory(LEGACY_KEYWORD, source=source))

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic.message == (
        "Invalid documentation in 'Legacy Layout': Not having an empty row before 'Tags:' is deprecated."
    )
    assert diagnostic.severity == DiagnosticSeverity.WARNING
    assert diagnostic.tags == [DiagnosticTag.DEPRECATED]
    assert diagnostic.range == Range(start=Position(line=3, character=11), end=Position(line=3, character=21))


@needs_rf_75
def test_row_after_a_continued_row_is_found(analyzer_factory: Callable[..., AnalyzerResult]) -> None:
    """A row ending with a backslash continues on the next row, so the `Tags:` line is on the third row."""
    text = """\
*** Keywords ***
Continued
    [Documentation]    Does \\
    ...    something.
    ...    Tags: a
    No Operation
"""
    diagnostics = _tags_diagnostics(analyzer_factory(text))

    assert [d.range.start for d in diagnostics] == [Position(line=4, character=11)]


@needs_rf_75
@pytest.mark.parametrize(
    "documentation",
    [
        pytest.param("[Documentation]    Does something.\n    ...\n    ...    Tags: a, b", id="empty row before"),
        pytest.param("[Documentation]    Tags: a, b", id="first row"),
        pytest.param(
            "[Documentation]    Does something.\n    ...\n    ...    Args:\n"
            "    ...        x: the x\n    ...    Tags: a",
            id="after an args section",
        ),
    ],
)
def test_correct_layouts_are_not_reported(analyzer_factory: Callable[..., AnalyzerResult], documentation: str) -> None:
    text = f"*** Keywords ***\nCorrect Layout\n    {documentation}\n    No Operation\n"

    assert _tags_diagnostics(analyzer_factory(text)) == []


@needs_rf_75
@pytest.mark.parametrize(
    "text",
    [
        pytest.param(
            "*** Settings ***\nDocumentation    Does something.\n...    Tags: a, b\n",
            id="suite or resource file",
        ),
        pytest.param(
            "*** Test Cases ***\nA Test\n    [Documentation]    Does something.\n    ...    Tags: a, b\n"
            "    No Operation\n",
            id="test",
        ),
    ],
)
def test_other_documentation_is_not_checked(analyzer_factory: Callable[..., AnalyzerResult], text: str) -> None:
    assert _tags_diagnostics(analyzer_factory(text)) == []


@pytest.mark.skipif(RF_VERSION >= (7, 5), reason="Robot Framework warns about the layout since 7.5")
def test_nothing_is_reported_on_older_robot(analyzer_factory: Callable[..., AnalyzerResult]) -> None:
    assert _tags_diagnostics(analyzer_factory(LEGACY_KEYWORD)) == []


@needs_rf_75
def test_diagnostic_can_be_suppressed(analyzer_factory: Callable[..., AnalyzerResult]) -> None:
    text = LEGACY_KEYWORD.replace("Tags: a, b", "Tags: a, b    # robotcode: ignore[TagsWithoutEmptyRow]")
    diagnostics = _tags_diagnostics(analyzer_factory(text))
    assert len(diagnostics) == 1

    assert DiagnosticsModifier(parse_robot(text)).modify_diagnostics(diagnostics) == []
