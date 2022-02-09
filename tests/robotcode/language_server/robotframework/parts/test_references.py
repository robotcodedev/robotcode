from pathlib import Path
from typing import Optional

import pytest
from pytest_regressions.data_regression import DataRegressionFixture

from robotcode.language_server.common.lsp_types import (
    Location,
    Position,
    ReferenceContext,
)
from robotcode.language_server.common.text_document import TextDocument
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
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/references.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
)
@pytest.mark.usefixtures("protocol")
@pytest.mark.asyncio
async def test(
    data_regression: DataRegressionFixture,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    def split(location: Optional[Location]) -> Optional[Location]:
        if location is None:
            return None

        return Location(location.uri, location.range)

    result = await protocol.robot_references.collect(
        protocol.robot_document_highlight,
        test_document,
        Position(line=data.line, character=data.character),
        ReferenceContext(include_declaration=True),
    )
    data_regression.check({"data": data, "result": [split(v) for v in result] if result else result})
