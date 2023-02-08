import asyncio
from pathlib import Path
from typing import Optional

import pytest
import yaml
from pytest_regtest import RegTestFixture

from robotcode.language_server.common.lsp_types import Hover, MarkupContent, Position
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.utils.async_tools import run_coroutine_in_thread

from ..tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)


def split(hover: Optional[Hover]) -> Optional[Hover]:
    if hover is None:
        return None
    if isinstance(hover.contents, MarkupContent):
        return Hover(
            MarkupContent(hover.contents.kind, hover.contents.value.splitlines()[0].split("=")[0].strip()),
            hover.range,
        )
    return hover


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/hover.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
    scope="module",
)
@pytest.mark.usefixtures("protocol")
@pytest.mark.asyncio()
async def test(
    regtest: RegTestFixture,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    result = await asyncio.wait_for(
        run_coroutine_in_thread(
            protocol.robot_hover.collect,
            protocol.hover,
            test_document,
            Position(line=data.line, character=data.character),
        ),
        60,
    )

    regtest.write(yaml.dump({"data": data, "result": split(result)}))
