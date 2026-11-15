"""Tests that the language server serves the Markdown files Robot Framework parses as a language of their own.

Each test runs its own language server session on a project in `tmp_path`, with Robot Framework's default extensions or
a profile that sets `extensions` or `parse-include`, and opens the files with the language id `markdown`, as editors do.
"""

from pathlib import Path
from typing import List

import pytest

from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import Hover, MarkupContent, Position, TextDocumentItem
from robotcode.core.uri import Uri
from robotcode.language_server.common.parts.diagnostics import DiagnosticsCollectType
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.document_formats import MARKDOWN_LANGUAGE_ID, MARKDOWN_SUPPORTED
from tests.robotcode.language_server.robotframework.tools import document_of, language_server, write_project

requires_markdown = pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="Markdown needs Robot Framework 7.5.1")

SHOP = """\
# Shop

```robot
*** Test Cases ***
Buy
    Undefined Keyword
    Log    hello
```
"""


def _open_as_markdown(protocol: RobotLanguageServerProtocol, path: Path) -> None:
    protocol.documents._text_document_did_open(TextDocumentItem(path.as_uri(), "markdown", 1, SHOP))


def _diagnostic_codes(protocol: RobotLanguageServerProtocol, path: Path) -> List[str]:
    document = document_of(protocol, path)
    return sorted(
        str(d.code)
        for result in protocol.diagnostics.collect(
            protocol.diagnostics,
            document,
            DiagnosticsCollectType.NORMAL,
            callback_filter=language_id_filter(document),
            return_exceptions=True,
        )
        if result is not None and not isinstance(result, BaseException)
        for d in result.diagnostics or []
    )


def _hovers(protocol: RobotLanguageServerProtocol, path: Path, position: Position) -> List[str]:
    document = document_of(protocol, path)
    hovers = protocol.hover.collect(protocol.hover, document, position, callback_filter=language_id_filter(document))
    return [h.contents.value for h in hovers if isinstance(h, Hover) and isinstance(h.contents, MarkupContent)]


@requires_markdown
def test_a_markdown_suite_opened_as_markdown_gets_the_markdown_language(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"other/placeholder.txt": ""})
    shop = project / "shop.robot.md"
    with language_server(project) as protocol:
        _open_as_markdown(protocol, shop)

        assert document_of(protocol, shop).language_id == MARKDOWN_LANGUAGE_ID
        assert "KeywordNotFound" in _diagnostic_codes(protocol, shop)
        assert any("Logs the given message" in h for h in _hovers(protocol, shop, Position(6, 5)))


@requires_markdown
def test_the_preload_opens_only_the_markdown_files_robot_framework_parses(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"README.md": SHOP, "shop.robot.md": SHOP})
    with language_server(project) as protocol:
        assert protocol.documents.get(Uri.from_path(project / "shop.robot.md").normalized()) is not None
        assert protocol.documents.get(Uri.from_path(project / "README.md").normalized()) is None


@requires_markdown
def test_a_markdown_file_of_an_inactive_extension_is_not_served(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"other/placeholder.txt": ""})
    readme = project / "README.md"
    with language_server(project) as protocol:
        _open_as_markdown(protocol, readme)

        assert document_of(protocol, readme).language_id == "unknown"
        assert _diagnostic_codes(protocol, readme) == []
        assert _hovers(protocol, readme, Position(6, 5)) == []


def test_extensions_without_a_markdown_extension_serves_no_markdown_file(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"shop.robot.md": SHOP})
    shop = project / "shop.robot.md"
    with language_server(project, profile=RobotBaseProfile(extensions="robot")) as protocol:
        assert protocol.documents.get(Uri.from_path(shop).normalized()) is None

        _open_as_markdown(protocol, shop)

        assert document_of(protocol, shop).language_id == "unknown"
        assert _diagnostic_codes(protocol, shop) == []
        assert _hovers(protocol, shop, Position(6, 5)) == []


@requires_markdown
def test_a_markdown_file_outside_the_parse_include_patterns_is_not_served(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = write_project(tmp_path, {"other/placeholder.txt": ""})
    guide = project / "docs" / "guide.md"
    readme = project / "README.md"
    # the language server runs in the project root, from which Robot Framework takes relative patterns
    monkeypatch.chdir(project)
    with language_server(project, profile=RobotBaseProfile(parse_include=["docs/*.md"])) as protocol:
        _open_as_markdown(protocol, guide)
        _open_as_markdown(protocol, readme)

        assert document_of(protocol, guide).language_id == MARKDOWN_LANGUAGE_ID
        assert "KeywordNotFound" in _diagnostic_codes(protocol, guide)
        assert document_of(protocol, readme).language_id == "unknown"
        assert _diagnostic_codes(protocol, readme) == []
