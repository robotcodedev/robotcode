from pathlib import Path

import pytest
import yaml

from robotcode.core.lsp.types import Position
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
from .test_goto_implementation import split


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/goto.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
    scope="module",
)
def test_definition(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    result = protocol.robot_goto.collect_definition(
        protocol.robot_goto,
        test_document,
        Position(line=data.line, character=data.character),
    )

    regtest.write(yaml.dump({"data": data, "result": split(result)}))
