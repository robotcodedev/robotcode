"""Tests for the Markdown content of the documentation view."""

from pathlib import Path

from robotcode.language_server.robotframework.parts.http_server import library_doc_to_markdown_content
from robotcode.robot.diagnostics.library_doc import get_library_doc

MARKDOWN_LIBRARY = '''\
"""Intro, see [Set Log Level] and [A section].

# A section

Text.
"""

ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"


def set_log_level():
    """Sets the level."""


def log():
    """Logs, see [Set Log Level]."""
'''


def test_references_link_to_the_headings_of_the_page(tmp_path: Path) -> None:
    lib_file = tmp_path / "MarkdownViewLib.py"
    lib_file.write_text(MARKDOWN_LIBRARY, encoding="utf-8")

    content = library_doc_to_markdown_content(get_library_doc(str(lib_file)))

    assert "Intro, see [Set Log Level](#set-log-level) and [A section](#a-section)." in content
    assert "Logs, see [Set Log Level](#set-log-level)." in content
    # the headings the links point to
    assert "\n## A section\n" in content
    assert "\n# Set Log Level\n" in content
