import asyncio
from pathlib import Path
from typing import Union

import pytest
import yaml
from pytest_regtest import RegTestFixture

from robotcode.language_server.common.lsp_types import (
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    CodeActionTriggerKind,
    Command,
    Position,
    Range,
)
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from tests.robotcode.language_server.robotframework.tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/code_action_show_documentation.robot")),
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
    def split(action: Union[Command, CodeAction]) -> Union[Command, CodeAction]:
        if isinstance(action, CodeAction) and action.command is not None and action.command.arguments:
            action.command.arguments = ["<removed>"]
        return action

    result = await asyncio.wait_for(
        protocol.robot_code_action_documentation.collect(
            protocol.robot_code_action_documentation,
            test_document,
            Range(
                Position(line=data.line, character=data.character), Position(line=data.line, character=data.character)
            ),
            CodeActionContext(
                diagnostics=[], only=[CodeActionKind.SOURCE.value], trigger_kind=CodeActionTriggerKind.INVOKED
            ),
        ),
        60,
    )
    regtest.write(
        yaml.dump(
            {
                "data": data,
                "result": sorted(
                    (split(v) for v in result), key=lambda v: (v.title, v.kind if isinstance(v, CodeAction) else None)
                )
                if result
                else result,
            }
        )
    )
