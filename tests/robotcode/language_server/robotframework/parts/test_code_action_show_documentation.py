import os
from pathlib import Path
from typing import Any, Dict, Union

import pytest
import yaml

from robotcode.core.lsp.types import (
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    CodeActionTriggerKind,
    Command,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.parts.code_action_documentation import DocumentationTarget
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from tests.robotcode.language_server.robotframework.tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)

from .pytest_regtestex import RegTestFixtureEx

DATA_PATH = Path(Path(__file__).absolute().parent, "data")


def _relative(path: Path) -> str:
    return Path(os.path.relpath(path, DATA_PATH)).as_posix()


def _target(target: DocumentationTarget) -> Dict[str, Any]:
    name = Path(target.name)
    return {
        "uri": _relative(Uri(target.uri).to_path()),
        "name": _relative(name) if name.is_absolute() else target.name,
        "args": target.args,
        "baseDir": _relative(Path(target.base_dir)) if target.base_dir is not None else None,
        "keyword": target.keyword,
    }


@pytest.mark.parametrize(
    ("test_document", "data"),
    list(
        generate_tests_from_source_document(
            Path(
                Path(__file__).parent,
                "data/tests/code_action_show_documentation.robot",
            )
        )
    ),
    indirect=["test_document"],
    ids=generate_test_id,
    scope="module",
)
def test(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    def split(action: Union[Command, CodeAction]) -> Union[Command, CodeAction]:
        if isinstance(action, CodeAction) and action.command is not None and action.command.arguments:
            argument = action.command.arguments[0]
            if isinstance(argument, DocumentationTarget):
                action.command.arguments = [_target(argument)]
            else:
                action.command.arguments = ["<removed>"]
        return action

    result = protocol.robot_code_action_documentation.collect(
        protocol.robot_code_action_documentation,
        test_document,
        Range(
            Position(line=data.line, character=data.character),
            Position(line=data.line, character=data.character),
        ),
        CodeActionContext(
            diagnostics=[],
            only=[CodeActionKind.SOURCE.value],
            trigger_kind=CodeActionTriggerKind.INVOKED,
        ),
    )
    regtest.write(
        yaml.dump(
            {
                "data": data,
                "result": (
                    sorted(
                        (split(v) for v in result),
                        key=lambda v: (
                            v.title,
                            v.kind if isinstance(v, CodeAction) else None,
                        ),
                    )
                    if result
                    else result
                ),
            }
        )
    )
