import re
from pathlib import Path

import pytest

from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.common.types import MarkupContent, Position
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

from ..tools import generate_tests_from_source_document


@pytest.mark.parametrize(
    ("test_document", "name", "line", "character", "expression"),
    generate_tests_from_source_document(str(Path(Path(__file__).parent, "data/hover.robot"))),
    indirect=["test_document"],
)
@pytest.mark.asyncio
@pytest.mark.usefixtures("protocol")
async def test_hover(
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    name: str,
    line: int,
    character: int,
    expression: str,
) -> None:
    result = await protocol._robot_hover.collect(
        protocol.hover, test_document, Position(line=line, character=character)
    )

    assert bool(
        eval(
            expression,
            {"re": re},
            {
                "result": result,
                "value": result.contents.value
                if result is not None and isinstance(result.contents, MarkupContent)
                else None,
                "line": line,
                "character": character,
            },
        )
    ), expression
