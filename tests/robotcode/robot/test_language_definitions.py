"""Tests for the languages RobotCode serves."""

from pathlib import Path

import pytest

from robotcode.core.language import LanguageDefinition
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from robotcode.robot.language_definitions import markdown_language_definition

requires_markdown = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")


@requires_markdown
def test_the_markdown_language_has_the_active_extensions(tmp_path: Path) -> None:
    assert markdown_language_definition(RobotBaseProfile(), tmp_path) == LanguageDefinition(
        id="robotframework-markdown", extensions=[".robot.md"], extensions_ignore_case=True
    )


@requires_markdown
def test_the_markdown_language_has_the_condition_of_the_parse_include_patterns(tmp_path: Path) -> None:
    definition = markdown_language_definition(RobotBaseProfile(parse_include=["docs/*.md"]), tmp_path)

    assert definition is not None
    assert definition.file_condition is not None
    assert definition.file_condition(tmp_path / "docs" / "guide.md")
    assert not definition.file_condition(tmp_path / "README.md")


def test_no_markdown_language_without_an_active_format(tmp_path: Path) -> None:
    assert markdown_language_definition(RobotBaseProfile(extensions="robot"), tmp_path) is None
