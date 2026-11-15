"""Regression tests of the editor features in a Markdown suite.

The suite lies in its own data folder, whose robot.toml switches on the Markdown format, and is served by a language
server of its own. The baselines show the positions in the file.
"""

import shutil
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple

import pytest
import yaml

from robotcode.core.lsp.types import (
    DocumentSymbol,
    Hover,
    Location,
    LocationLink,
    MarkupContent,
    Position,
    ReferenceContext,
)
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.config.loader import load_robot_config_from_path
from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from tests.robotcode.language_server.robotframework.tools import (
    GeneratedTestData,
    document_of,
    generate_test_id,
    generate_tests_from_source_document,
    language_server,
)

from .pytest_regtestex import RegTestFixtureEx

pytestmark = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")

DATA = Path(Path(__file__).absolute().parent, "data_markdown")
SHOP = DATA / "shop.robot.md"

MARKERS = [data for _, data in generate_tests_from_source_document(SHOP)]


@pytest.fixture(scope="module")
def shop() -> Iterator[Tuple[RobotLanguageServerProtocol, TextDocument]]:
    shutil.rmtree(DATA / ".robotcode_cache", ignore_errors=True)
    profile = load_robot_config_from_path(DATA / "robot.toml").combine_profiles().evaluated()
    with language_server(DATA, profile=profile) as protocol:
        yield protocol, document_of(protocol, SHOP)


def _hover(hover: Optional[Hover]) -> Any:
    # the first line of the documentation is enough to see which keyword or variable the hover shows
    if hover is None or not isinstance(hover.contents, MarkupContent):
        return hover
    return {"range": hover.range, "first_line": hover.contents.value.strip().splitlines()[0]}


def _location(location: Any) -> Any:
    if isinstance(location, LocationLink):
        return {"target": Path(location.target_uri).name, "range": location.target_selection_range}
    if isinstance(location, Location):
        return {"target": Path(location.uri).name, "range": location.range}
    return location


@pytest.mark.parametrize("data", MARKERS, ids=generate_test_id)
def test_hover(
    regtest: RegTestFixtureEx, shop: Tuple[RobotLanguageServerProtocol, TextDocument], data: GeneratedTestData
) -> None:
    protocol, document = shop
    result = protocol.robot_hover.collect(protocol.hover, document, Position(data.line, data.character))

    regtest.write(yaml.dump({"data": data, "result": _hover(result)}))


@pytest.mark.parametrize("data", MARKERS, ids=generate_test_id)
def test_definition(
    regtest: RegTestFixtureEx, shop: Tuple[RobotLanguageServerProtocol, TextDocument], data: GeneratedTestData
) -> None:
    protocol, document = shop
    result = protocol.robot_goto.collect_definition(protocol.robot_goto, document, Position(data.line, data.character))

    locations: List[Any] = result if isinstance(result, list) else [result] if result else []
    regtest.write(yaml.dump({"data": data, "result": [_location(r) for r in locations]}))


@pytest.mark.parametrize("data", MARKERS, ids=generate_test_id)
def test_references(
    regtest: RegTestFixtureEx, shop: Tuple[RobotLanguageServerProtocol, TextDocument], data: GeneratedTestData
) -> None:
    protocol, document = shop
    result = protocol.robot_references.collect(
        protocol.robot_references, document, Position(data.line, data.character), ReferenceContext(True)
    )

    regtest.write(
        yaml.dump(
            {
                "data": data,
                "result": sorted((_location(r) for r in result or []), key=lambda r: (r["target"], r["range"].start)),
            }
        )
    )


def test_semantic_tokens(regtest: RegTestFixtureEx, shop: Tuple[RobotLanguageServerProtocol, TextDocument]) -> None:
    protocol, document = shop
    result = protocol.robot_semantic_tokens.collect_full(protocol.robot_semantic_tokens, document)

    regtest.write(yaml.dump({"result": result}))


def _symbols(symbols: Any) -> List[Any]:
    # flat, with the depth of each symbol; a symbol is one of its own children
    def walk(symbol: DocumentSymbol, depth: int) -> Iterator[Any]:
        yield {"depth": depth, "name": symbol.name, "kind": symbol.kind, "range": symbol.range}
        for child in symbol.children or []:
            if child is not symbol:
                yield from walk(child, depth + 1)

    return [x for s in symbols or [] if isinstance(s, DocumentSymbol) for x in walk(s, 0)]


def test_document_symbols(regtest: RegTestFixtureEx, shop: Tuple[RobotLanguageServerProtocol, TextDocument]) -> None:
    protocol, document = shop
    result = protocol.markdown_document_symbols.collect(protocol.document_symbols, document)

    regtest.write(yaml.dump({"result": _symbols(result)}))
