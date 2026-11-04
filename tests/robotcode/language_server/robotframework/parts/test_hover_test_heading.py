"""Tests for the heading in the hover of a test or task name."""

from pathlib import Path
from typing import Callable

from robotcode.core.lsp.types import MarkupContent, Position
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)


def _hover_first_line(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    file: Path,
    suite: str,
    line: int,
) -> str:
    file.write_text(suite, encoding="utf-8")
    document = open_temp_document(file)
    result = protocol.robot_hover.collect(protocol.hover, document, Position(line=line, character=2))

    assert result is not None
    assert isinstance(result.contents, MarkupContent)
    return result.contents.value.splitlines()[0]


def test_test_name_is_italic_and_keeps_its_characters(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    suite = "*** Test Cases ***\nRun *this* <now> __init__\n    No Operation\n"

    assert _hover_first_line(protocol, open_temp_document, tmp_path / "heading_name.robot", suite, 1) == (
        "## Test Case *Run \\*this\\* \\<now> \\_\\_init\\_\\_*"
    )


def test_task_name_has_its_own_heading(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    suite = "*** Tasks ***\nClean up\n    No Operation\n"

    assert _hover_first_line(protocol, open_temp_document, tmp_path / "heading_task.robot", suite, 1) == (
        "## Task *Clean up*"
    )


def test_variable_in_the_test_name_is_replaced(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    suite = "*** Variables ***\n${OWNER}    core\n\n*** Test Cases ***\nOwned by ${OWNER}\n    No Operation\n"

    assert _hover_first_line(protocol, open_temp_document, tmp_path / "heading_variable.robot", suite, 4) == (
        "## Test Case *Owned by core*"
    )
