"""Tests for the built-in variables offered by variable completion."""

from pathlib import Path
from typing import Callable, Set

from robotcode.core.lsp.types import CompletionList, Position, TextEdit
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.robot.utils import RF_VERSION

SUITE = """\
*** Test Cases ***
With Metadata
    Log    ${}
"""


def _offered_variable_names(
    protocol: RobotLanguageServerProtocol, document: TextDocument, position: Position
) -> Set[str]:
    result = protocol.robot_completion.collect(protocol.completion, document, position, None)

    assert result is not None
    items = result.items if isinstance(result, CompletionList) else result
    return {item.text_edit.new_text for item in items if isinstance(item.text_edit, TextEdit)}


def test_test_metadata_is_offered_since_rf_75(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    file = tmp_path / "test_metadata_completion.robot"
    file.write_text(SUITE, encoding="utf-8")

    names = _offered_variable_names(
        protocol, open_temp_document(file), Position(line=2, character=len("    Log    ${"))
    )

    assert "SUITE_METADATA" in names
    assert ("TEST_METADATA" in names) == (RF_VERSION >= (7, 5))
