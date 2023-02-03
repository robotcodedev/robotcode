from pathlib import Path

import pytest
import yaml
from pytest_regtest import RegTestFixture

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
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/references.robot")),
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
    def split(location: Location) -> Location:
        return Location("/".join(location.uri.split("/")[-2:]), location.range)

    result = await protocol.robot_references.collect(
        protocol.robot_references,
        test_document,
        Position(line=data.line, character=data.character),
        ReferenceContext(include_declaration=True),
    )
    regtest.write(
        yaml.dump(
            {
                "data": data,
                "result": sorted((split(v) for v in result), key=lambda v: (v.uri, v.range.start, v.range.end))
                if result
                else result,
            }
        )
    )
