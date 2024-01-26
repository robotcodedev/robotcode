import dataclasses
from pathlib import Path
from typing import Iterator, List, Optional, Union

import pytest
import yaml

from robotcode.core.lsp.types import DocumentSymbol, Position, SymbolInformation
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from tests.robotcode.language_server.robotframework.tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)

from .pytest_regtestex import RegTestFixtureEx


def split(
    values: Optional[Union[List[DocumentSymbol], List[SymbolInformation]]],
    data: GeneratedTestData,
) -> Iterator[Optional[Union[DocumentSymbol, SymbolInformation]]]:
    p = Position(data.line, data.character)

    for value in values or []:
        if isinstance(value, DocumentSymbol):
            if p in value.range:
                yield dataclasses.replace(value, children=[])

            if value.children:
                yield from split(value.children, data)

        elif isinstance(value, SymbolInformation):
            if p in value.location.range:
                yield dataclasses.replace(
                    value,
                    location=dataclasses.replace(
                        value.location,
                        uri=Uri(value.location.uri).to_path().name,
                    ),
                )


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/symbols.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
    scope="module",
)
def test(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    result = protocol.robot_document_symbols.collect(protocol.hover, test_document)

    regtest.write(
        yaml.dump(
            {
                "data": data,
                "result": (
                    next(
                        reversed([l for l in split(result, data) if l is not None]),
                        None,
                    )
                    if result
                    else result
                ),
            }
        )
    )
