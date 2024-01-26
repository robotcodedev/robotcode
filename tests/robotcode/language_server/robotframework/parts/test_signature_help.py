import dataclasses
from pathlib import Path

import pytest
import yaml

from robotcode.core.lsp.types import (
    Position,
    SignatureHelpContext,
    SignatureHelpTriggerKind,
)
from robotcode.core.text_document import TextDocument
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
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/signature_help.robot")),
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
    result = protocol.robot_signature_help.collect(
        protocol.robot_signature_help,
        test_document,
        Position(line=data.line, character=data.character),
        SignatureHelpContext(trigger_kind=SignatureHelpTriggerKind.INVOKED, is_retrigger=False),
    )

    regtest.write(
        yaml.dump(
            {
                "data": data,
                "result": (
                    dataclasses.replace(
                        result,
                        signatures=[
                            dataclasses.replace(
                                s,
                                documentation=None,
                                parameters=(
                                    [dataclasses.replace(p, documentation=None) for p in s.parameters]
                                    if s.parameters
                                    else s.parameters
                                ),
                            )
                            for s in result.signatures
                        ],
                    )
                    if result
                    else None
                ),
            }
        )
    )
