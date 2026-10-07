"""Tests for two libraries that are classes of one module.

Both imports have the same source file, but they are different libraries:
the hover, the definition, the highlights and the references of an import
are those of its own library. Another import of the same library stays a
reference of the first import.
"""

from pathlib import Path
from typing import Callable, List, Tuple

import pytest

from robotcode.core.lsp.types import LocationLink, MarkupContent, Position, ReferenceContext
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol

SUITE = """\
*** Settings ***
Library    mylibs.LoginLib
Library    mylibs.OrderLib
Library    mylibs.LoginLib    WITH NAME    AnotherLogin

*** Test Cases ***
First
    Login    alice
    Place Order    book
"""

MYLIBS = '''\
class LoginLib:
    """Logs users in."""

    def login(self, user):
        pass


class OrderLib:
    """Places orders."""

    def place_order(self, item):
        pass
'''

# the lines of the imports in SUITE and of the classes in MYLIBS
LOGIN, ORDER, ANOTHER_LOGIN = 1, 2, 3
LOGIN_CLASS, ORDER_CLASS = 0, 7


@pytest.fixture(params=[False, True], ids=["legacy", "model"])
def document(
    request: pytest.FixtureRequest,
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> TextDocument:
    monkeypatch.setattr(protocol.documents_cache.analysis_config, "semantic_model", request.param)
    # imported by module name; the process that loads a library starts with this search path
    monkeypatch.syspath_prepend(str(tmp_path))
    (tmp_path / "mylibs.py").write_text(MYLIBS, encoding="utf-8")
    (tmp_path / "suite.robot").write_text(SUITE, encoding="utf-8")
    return open_temp_document(tmp_path / "suite.robot")


def _on_import(line: int) -> Position:
    return Position(line=line, character=len("Library    ") + 1)


def _hover_heading(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> str:
    hover = protocol.robot_hover.collect(protocol.robot_hover, document, _on_import(line))
    assert hover is not None
    assert isinstance(hover.contents, MarkupContent)
    return hover.contents.value.splitlines()[0]


def _definitions(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> List[Tuple[str, int]]:
    result = protocol.robot_goto.collect_definition(protocol.robot_goto, document, _on_import(line))
    assert result
    return [
        (Uri(d.target_uri).to_path().name, d.target_selection_range.start.line)
        if isinstance(d, LocationLink)
        else (Uri(d.uri).to_path().name, d.range.start.line)
        for d in (result if isinstance(result, list) else [result])
    ]


def _highlights(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> List[int]:
    result = protocol.robot_document_highlight.collect(protocol.robot_document_highlight, document, _on_import(line))
    return sorted(h.range.start.line for h in result or [])


def _references(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> List[int]:
    result = protocol.robot_references.collect(
        protocol.robot_references, document, _on_import(line), ReferenceContext(include_declaration=False)
    )
    return sorted(r.range.start.line for r in result or [] if Uri(r.uri).to_path().name == "suite.robot")


def test_the_hover_of_an_import_shows_its_own_library(
    protocol: RobotLanguageServerProtocol, document: TextDocument
) -> None:
    assert _hover_heading(protocol, document, LOGIN) == "### Library *mylibs.LoginLib*"
    assert _hover_heading(protocol, document, ORDER) == "### Library *mylibs.OrderLib*"


def test_the_definition_of_an_import_is_its_class(
    protocol: RobotLanguageServerProtocol, document: TextDocument
) -> None:
    assert _definitions(protocol, document, LOGIN) == [("mylibs.py", LOGIN_CLASS)]
    assert _definitions(protocol, document, ORDER) == [("mylibs.py", ORDER_CLASS)]


def test_highlights_and_references_keep_the_libraries_apart(
    protocol: RobotLanguageServerProtocol, document: TextDocument
) -> None:
    # the second import of LoginLib is a reference of the first one
    assert _highlights(protocol, document, LOGIN) == [LOGIN, ANOTHER_LOGIN]
    assert _highlights(protocol, document, ORDER) == [ORDER]
    assert _references(protocol, document, LOGIN) == [LOGIN, ANOTHER_LOGIN]
    assert _references(protocol, document, ORDER) == [ORDER]
