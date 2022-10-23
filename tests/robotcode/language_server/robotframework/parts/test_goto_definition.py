from pathlib import Path

import pytest
from pytest_regressions.data_regression import DataRegressionFixture

from robotcode.language_server.common.lsp_types import Position
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

from ..tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)
from .test_goto_implementation import split


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/goto.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
    scope="module",
)
@pytest.mark.usefixtures("protocol")
@pytest.mark.asyncio
async def test_definition(
    data_regression: DataRegressionFixture,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:

    result = await protocol.robot_goto.collect_definition(
        protocol.robot_goto,
        test_document,
        Position(line=data.line, character=data.character),
    )

    data_regression.check({"data": data, "result": split(result)})
