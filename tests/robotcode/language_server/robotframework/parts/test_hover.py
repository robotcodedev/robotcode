import re
from pathlib import Path

import pytest

from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.common.types import MarkupContent, Position
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

from ..tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/hover.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
)
@pytest.mark.asyncio
@pytest.mark.usefixtures("protocol")
async def test_hover(
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    result = await protocol._robot_hover.collect(
        protocol.hover, test_document, Position(line=data.line, character=data.character)
    )

    assert bool(
        eval(
            data.expression,
            {"re": re},
            {
                "result": result,
                "value": result.contents.value
                if result is not None and isinstance(result.contents, MarkupContent)
                else None,
                "line": data.line,
                "character": data.character,
            },
        )
    ), f"{data.expression} == {repr(result)}"
