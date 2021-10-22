import re
from pathlib import Path

import pytest

from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.common.types import Position
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

from ..tools import generate_tests_from_source_document


@pytest.mark.parametrize(
    ("test_document", "name", "line", "character", "expression"),
    generate_tests_from_source_document(str(Path(Path(__file__).parent, "data/goto.robot"))),
    indirect=["test_document"],
)
@pytest.mark.asyncio
@pytest.mark.usefixtures("protocol")
async def test_goto(
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    name: str,
    line: int,
    character: int,
    expression: str,
) -> None:
    result = await protocol._robot_goto.collect(
        protocol._robot_goto, test_document, Position(line=line, character=character)
    )

    assert bool(
        eval(
            expression,
            {"re": re},
            {
                "result": result,               
                "line": line,
                "character": character,
            },
        )
    ), f"{expression}  {repr(result)}"
