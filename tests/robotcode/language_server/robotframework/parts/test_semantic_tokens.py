import functools
from pathlib import Path

import pytest
import yaml

from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

from ..tools import (
    generate_test_id_with_path,
)
from .pytest_regtestex import RegTestFixtureEx

base_path = Path(Path(__file__).parent, "data/tests")


@pytest.mark.parametrize(
    ("test_document"),
    [
        *(f for f in base_path.glob("*.robot")),
        *(f for f in base_path.glob("versions/**/*.robot")),
    ],
    indirect=["test_document"],
    ids=functools.partial(generate_test_id_with_path, base_path),
    scope="module",
)
def test(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
) -> None:
    result = protocol.robot_semantic_tokens.collect_full(
        protocol.robot_semantic_tokens,
        test_document,
    )

    regtest.write(yaml.dump({"result": result}))
