from pathlib import Path

import pytest
import yaml

from robotcode.core.lsp.types import Location, Position, ReferenceContext
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


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/references.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
    scope="module",
)
@pytest.mark.usefixtures("protocol")
def test(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    def split(location: Location) -> Location:
        return Location("/".join(location.uri.split("/")[-2:]), location.range)

    result = protocol.robot_references.collect(
        protocol.robot_references,
        test_document,
        Position(line=data.line, character=data.character),
        ReferenceContext(include_declaration=True),
    )
    regtest.write(
        yaml.dump(
            {
                "data": data,
                "result": sorted(
                    (split(v) for v in result),
                    key=lambda v: (v.uri, v.range.start, v.range.end),
                )
                if result
                else result,
            }
        )
    )
