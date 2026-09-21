"""Tests for the Metadata block in the hover of a test name (Robot Framework 7.5)."""

from pathlib import Path
from typing import Callable

import pytest

from robotcode.core.lsp.types import MarkupContent, Position
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.robot.utils import RF_VERSION

SUITE = """\
*** Variables ***
${OWNER}    core

*** Test Cases ***
With Metadata
    [Documentation]    Some documentation
    [Tags]    smoke
    [Metadata]    Issue    4409
    [Metadata]    Owner Team    ${OWNER}
    [Metadata]    Description    first line
    ...    second line
    No Operation

Plain Test
    [Tags]    smoke
    No Operation

Empty Setting
    [Metadata]
    No Operation
"""


def _hover_text(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> str:
    result = protocol.robot_hover.collect(protocol.hover, document, Position(line=line, character=2))

    assert result is not None
    assert isinstance(result.contents, MarkupContent)
    return result.contents.value


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="test-level [Metadata] needs Robot Framework 7.5")
def test_test_name_hover_shows_metadata(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    file = tmp_path / "test_metadata_hover.robot"
    file.write_text(SUITE, encoding="utf-8")
    document = open_temp_document(file)

    with_metadata = _hover_text(protocol, document, 4)

    assert "Some documentation" in with_metadata
    assert "**Tags**: smoke" in with_metadata
    assert "**Metadata**:" in with_metadata
    assert "- Issue: 4409" in with_metadata.splitlines()
    assert "- Owner Team: core" in with_metadata.splitlines()
    # the lines of a multi-line value stay in one list item
    assert "- Description: first line second line" in with_metadata.splitlines()

    without_metadata = _hover_text(protocol, document, 13)

    assert "**Tags**: smoke" in without_metadata
    assert "Metadata" not in without_metadata

    # a `[Metadata]` setting with nothing after it is no metadata
    assert "Metadata" not in _hover_text(protocol, document, 17)


DUPLICATES_SUITE = """\
*** Test Cases ***
Duplicates
    [Metadata]    Owner Team    core
    [Metadata]    Issue    4409
    [Metadata]    issue    4410
    [Metadata]    owner_team    platform
    [Metadata]    IS SUE    4411
    No Operation
"""


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="test-level [Metadata] needs Robot Framework 7.5")
def test_hover_shows_the_metadata_robot_framework_reports(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    """Metadata names are case, space and underscore insensitive: the first
    spelling is kept, the last value wins, entries are sorted by name."""
    from robot.api import TestSuite

    file = tmp_path / "test_metadata_duplicates.robot"
    file.write_text(DUPLICATES_SUITE, encoding="utf-8")

    hover = _hover_text(protocol, open_temp_document(file), 1)
    entries = [line[2:] for line in hover.splitlines() if line.startswith("- ")]

    assert entries == ["Issue: 4411", "Owner Team: platform"]
    # exactly what Robot Framework itself has for this test, in its order
    robot_metadata = TestSuite.from_file_system(str(file)).tests[0].metadata  # type: ignore[attr-defined,unused-ignore]
    assert entries == [f"{name}: {value}" for name, value in robot_metadata.items()]
