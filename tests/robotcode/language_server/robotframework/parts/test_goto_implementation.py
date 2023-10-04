import asyncio
from pathlib import Path
from typing import List, Union, cast

import pytest
import yaml
from robotcode.core.lsp.types import Location, LocationLink, Position
from robotcode.core.uri import Uri
from robotcode.language_server.common.text_document import TextDocument
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
    result: Union[Location, LocationLink, List[Location], List[LocationLink], None]
) -> Union[Location, LocationLink, List[Location], List[LocationLink], None]:
    if result is None:
        return None
    if isinstance(result, Location):
        return Location((Uri(result.uri).to_path().name), result.range)
    if isinstance(result, LocationLink):
        return LocationLink(
            Uri(result.target_uri).to_path().name,
            result.target_range,
            result.target_selection_range,
            result.origin_selection_range,
        )
    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], LocationLink):
        return cast(List[LocationLink], [split(v) for v in result])

    if isinstance(result, list) and len(result) > 0 and isinstance(result[0], Location):
        return cast(List[Location], [split(v) for v in result])

    return result


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/goto.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
    scope="module",
)
@pytest.mark.usefixtures("protocol")
@pytest.mark.asyncio()
async def test_implementation(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    result = await asyncio.wait_for(
        protocol.robot_goto.collect_implementation(
            protocol.robot_goto,
            test_document,
            Position(line=data.line, character=data.character),
        ),
        60,
    )

    regtest.write(yaml.dump({"data": data, "result": split(result)}))
