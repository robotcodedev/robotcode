"""Tests for the links that show documentation in the Documentation Viewer."""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from robotcode.core.utils.dataclasses import as_json
from robotcode.language_server.robotframework.parts.code_action_documentation import (
    DOCUMENTATION_LINKS_SIZE_LIMIT,
    DocumentationTarget,
    documentation_link_resolver,
    documentation_viewer_link,
    documentation_viewer_uri,
    link_documentation,
    link_heading,
)
from robotcode.robot.diagnostics.library_doc import get_library_doc
from robotcode.robot.utils.markdown_docs import LinkResolver
from tests.robotcode.language_server.robotframework.viewer_links import (
    decoded_arguments,
    heading_target,
    viewer_links,
)


@pytest.mark.parametrize(
    "target",
    [
        DocumentationTarget(uri="file:///c%3A/Users/me/suite.robot", name="BuiltIn", keyword="Log"),
        DocumentationTarget(uri="file:///home/me/my%20project/suite.robot", name="Collections"),
        DocumentationTarget(
            uri="file:///home/me/suite.robot", name="./arglib.py", args=["a=50%25"], base_dir="/home/me"
        ),
        DocumentationTarget(
            uri="file:///home/me/a)b/suite.robot", name="lib.py", base_dir="/home/me/a)b", anchor="usage"
        ),
        DocumentationTarget(
            uri="file:///home/me/a%23b/suite.robot", name="lib.py", base_dir="/home/me/a#b", data_type="integer"
        ),
        DocumentationTarget(
            uri="file:///home/me/s%C3%A4tze/suite.robot", name="Bücher und 日本.resource", base_dir="/home/me/sätze"
        ),
    ],
)
def test_link_decodes_twice_to_the_target(target: DocumentationTarget) -> None:
    uri = documentation_viewer_uri(target)

    assert uri is not None
    assert decoded_arguments(uri) == json.loads(as_json([target]))
    # nothing in the query ends or breaks a Markdown link destination
    assert re.fullmatch(r"[A-Za-z0-9_.~%-]+", uri.partition("?")[2])
    assert documentation_viewer_link(target) == f'{uri} "Show in Documentation Viewer"'


def test_link_leaves_out_fields_without_a_value() -> None:
    uri = documentation_viewer_uri(DocumentationTarget(uri="file:///home/me/suite.robot", name="BuiltIn"))

    assert uri is not None
    assert decoded_arguments(uri) == [{"uri": "file:///home/me/suite.robot", "name": "BuiltIn", "args": []}]


def test_target_that_cannot_be_encoded_gives_no_link() -> None:
    target = DocumentationTarget(uri="file:///home/me/suite.robot", name="lib\udcff.py")

    assert documentation_viewer_uri(target) is None
    assert documentation_viewer_link(target) is None
    assert link_heading("### Library *lib*\n", target) == "### Library *lib*\n"


@pytest.mark.parametrize(
    ("markdown", "linked_text"),
    [
        ("### Keyword *Log*\n\n#### Arguments:", "Keyword *Log*"),
        ("### Library *BuiltIn*", "Library *BuiltIn*"),
        ("### Resource *common*\n", "Resource *common*"),
        ("### Keyword *Weird ] name [with\\ escape*\n", "Keyword *Weird \\] name \\[with\\\\ escape*"),
    ],
)
def test_heading_link(markdown: str, linked_text: str) -> None:
    target = DocumentationTarget(uri="file:///home/me/suite.robot", name="BuiltIn")
    link = documentation_viewer_link(target)

    first, _, rest = link_heading(markdown, target).partition("\n")

    assert first == f"### [{linked_text}]({link})"
    assert rest == markdown.partition("\n")[2]


@pytest.mark.parametrize(
    "markdown",
    ["#### Documentation:\ntext", "### Variables *vars.py*\n", "### Test Case *T*", "text ### Keyword *Log*"],
)
def test_heading_link_only_on_a_keyword_library_or_resource_heading(markdown: str) -> None:
    target = DocumentationTarget(uri="file:///home/me/suite.robot", name="BuiltIn")

    assert link_heading(markdown, target) == markdown


@pytest.mark.parametrize(("lines", "all_links"), [(10, True), (300, False)])
def test_documentation_too_long_for_links_keeps_only_the_heading_link(lines: int, all_links: bool) -> None:
    target = DocumentationTarget(uri="file:///home/me/suite.robot", name="BuiltIn")

    def render(link_resolver: Optional[LinkResolver]) -> str:
        link = link_resolver("keyword", "Log") if link_resolver is not None else None
        name = f"[Log]({link})" if link is not None else "`Log`"
        return "### Library *BuiltIn*\n\n" + "\n".join(f"See {name} and [usage](#usage)." for _ in range(lines))

    text = link_documentation(render, target, get_library_doc("BuiltIn"))

    heading = heading_target(text)
    assert heading is not None
    assert heading["name"] == "BuiltIn"
    if all_links:
        assert len(viewer_links(text)) == 1 + 2 * lines
    else:
        # with its links, the documentation would be longer than VS Code shows
        assert len(viewer_links(text)) == 1
        assert text.count("See `Log` and usage.") == lines
        assert len(text) < DOCUMENTATION_LINKS_SIZE_LIMIT


def test_size_limit_counts_utf16_code_units() -> None:
    """VS Code cuts at 100,000 UTF-16 code units; a character outside the BMP takes two of them."""
    target = DocumentationTarget(uri="file:///home/me/suite.robot", name="BuiltIn")

    def render(link_resolver: Optional[LinkResolver]) -> str:
        link = link_resolver("keyword", "Log") if link_resolver is not None else None
        name = f"[Log]({link})" if link is not None else "`Log`"
        return "### Library *BuiltIn*\n\n" + "\U0001f3f7" * (DOCUMENTATION_LINKS_SIZE_LIMIT // 2) + f" See {name}."

    text = link_documentation(render, target, get_library_doc("BuiltIn"))

    assert len(text) < DOCUMENTATION_LINKS_SIZE_LIMIT
    assert len(viewer_links(text)) == 1
    assert text.endswith(" See `Log`.")


SECTIONS_LIBRARY = '''\
class SectionsLib:
    """A library with sections.

    = Usage =

    How to use it.

    = ... =

    A section without letters.
    """

    def run(self):
        pass
'''


def test_section_links(tmp_path: Path) -> None:
    (tmp_path / "SectionsLib.py").write_text(SECTIONS_LIBRARY, encoding="utf-8")
    library_doc = get_library_doc(str(tmp_path / "SectionsLib.py"))
    target = DocumentationTarget(uri="file:///home/me/suite.robot", name="SectionsLib", keyword="Run")

    def target_of(link: Optional[str]) -> Optional[Dict[str, Any]]:
        return None if link is None else decoded_arguments(link.partition(" ")[0])[0]

    resolve = documentation_link_resolver(target, library_doc)
    assert (target_of(resolve("section", "Usage")) or {}).get("anchor") == "usage"
    # a title without letters or digits has no anchor: the page from its start
    without_anchor = target_of(resolve("section", "..."))
    assert without_anchor is not None
    assert "anchor" not in without_anchor
    assert "keyword" not in without_anchor

    # the page of a suite file has no introduction
    resolve = documentation_link_resolver(target, library_doc, introduction=False)
    assert resolve("section", "Usage") is None
    assert resolve("section", "Introduction") is None
    assert (target_of(resolve("section", "Keywords")) or {}).get("anchor") == "keywords"
