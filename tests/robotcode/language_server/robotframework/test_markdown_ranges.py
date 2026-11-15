"""Tests that completion and the ranges of a Markdown suite stay inside its code blocks.

The tests share one language server session on a project in a temporary folder, with a profile whose `extensions`
switch on the Markdown format, and ask the language server's parts as a request does, by the language of the document.
"""

from typing import Any, Iterator, List, Optional, Tuple

import pytest

from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import CompletionList, DocumentSymbol, Position, SelectionRange
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from tests.robotcode.language_server.robotframework.tools import document_of, language_server, write_project

pytestmark = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")

# the line numbers in the tests are 0-based, as the language server protocol counts them
SHOP = """\
# Keywords

```robot
*** Keywords ***
Greet
    Log    Hello

```

Some prose with Log

```robot

```

```robot
*** Test Cases ***
First
    Greet
```
"""

PROSE_LINE = 9
EMPTY_LINE_IN_BLOCK = 6
EMPTY_BLOCK_LINE = 12


@pytest.fixture(scope="module")
def shop(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Tuple[RobotLanguageServerProtocol, TextDocument]]:
    project = write_project(tmp_path_factory.mktemp("markdown_ranges"), {"shop.robot.md": SHOP})
    with language_server(project, profile=RobotBaseProfile(extensions="robot:robot.md")) as protocol:
        yield protocol, document_of(protocol, project / "shop.robot.md")


def _results(event: Any, document: TextDocument, *args: Any) -> List[Any]:
    # the results of the handlers for the document's language
    return [r for r in event(None, document, *args, callback_filter=language_id_filter(document)) if r is not None]


def _completion_labels(shop: Tuple[RobotLanguageServerProtocol, TextDocument], position: Position) -> List[str]:
    protocol, document = shop
    return [
        item.label
        for result in _results(protocol.completion.collect, document, position, None)
        for item in (result.items if isinstance(result, CompletionList) else result)
    ]


def _selection_ranges(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int, character: int) -> Any:
    return [
        r
        for result in _results(protocol.selection_range.collect, document, [Position(line, character)])
        for r in result
    ]


def test_no_completion_in_prose(shop: Tuple[RobotLanguageServerProtocol, TextDocument]) -> None:
    assert _completion_labels(shop, Position(PROSE_LINE, 0)) == []


@pytest.mark.parametrize("line", [EMPTY_LINE_IN_BLOCK, EMPTY_BLOCK_LINE], ids=["empty line", "block of an empty line"])
def test_completion_on_an_empty_line_of_a_block(
    shop: Tuple[RobotLanguageServerProtocol, TextDocument], line: int
) -> None:
    assert _completion_labels(shop, Position(line, 0)) != []


def test_the_folding_range_of_a_keyword_ends_in_its_block(
    shop: Tuple[RobotLanguageServerProtocol, TextDocument],
) -> None:
    protocol, document = shop
    ranges = [r for result in _results(protocol.folding_ranges.collect, document) for r in result]

    assert sorted((r.kind, r.start_line, r.end_line) for r in ranges) == [
        ("keyword", 4, EMPTY_LINE_IN_BLOCK),
        ("section", 3, EMPTY_LINE_IN_BLOCK),
        ("section", 16, 18),
        ("testcase", 17, 18),
    ]


def test_the_symbol_range_of_a_keyword_ends_in_its_block(
    shop: Tuple[RobotLanguageServerProtocol, TextDocument],
) -> None:
    protocol, document = shop
    symbols = [s for result in _results(protocol.document_symbols.collect, document) for s in result]

    def lines(symbol: DocumentSymbol) -> List[Tuple[str, int, int]]:
        children = [c for c in symbol.children or [] if c is not symbol]
        return [(symbol.name, symbol.range.start.line, symbol.range.end.line), *(x for c in children for x in lines(c))]

    assert [x for s in symbols if isinstance(s, DocumentSymbol) for x in lines(s)] == [
        ("Keywords", 3, EMPTY_LINE_IN_BLOCK),
        ("Greet", 4, EMPTY_LINE_IN_BLOCK),
        ("Test Cases", 16, 18),
        ("First", 17, 18),
    ]


def _selection_lines(selection: Optional[SelectionRange]) -> List[Tuple[int, int]]:
    result = []
    while selection is not None:
        result.append((selection.range.start.line, selection.range.end.line))
        selection = selection.parent
    return result


def test_selection_ranges_stay_inside_the_blocks(shop: Tuple[RobotLanguageServerProtocol, TextDocument]) -> None:
    protocol, document = shop

    assert _selection_ranges(protocol, document, PROSE_LINE, 3) == []

    (on_log,) = _selection_ranges(protocol, document, 5, 5)
    assert _selection_lines(on_log) == [(5, 5), (5, 5), (4, 6), (3, 6), (3, 18)]

    (on_empty_block,) = _selection_ranges(protocol, document, EMPTY_BLOCK_LINE, 0)
    assert all(start <= EMPTY_BLOCK_LINE <= end for start, end in _selection_lines(on_empty_block))
