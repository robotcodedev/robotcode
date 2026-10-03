"""Tests for completing the arguments of a keyword call: their names with documentation and their values."""

import sys
from pathlib import Path
from typing import Callable, Dict

import pytest

from robotcode.core.lsp.types import CompletionItem, CompletionList, MarkupContent, Position
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.robot.utils import RF_VERSION
from tests.robotcode.language_server.robotframework.viewer_links import heading_target, viewer_link

LIBRARY = '''\
def use_integer(base: int, level="INFO"):
    """Uses an integer.

    Args:
        base: The base of the number.
        level: The log level to use.
    """
'''

SUITE = """\
*** Settings ***
Library    DocumentedCompletionLib.py

*** Test Cases ***
First
    Use Integer    {arguments}
"""


def _resolved_items(
    protocol: RobotLanguageServerProtocol, document: TextDocument, position: Position
) -> Dict[str, CompletionItem]:
    result = protocol.robot_completion.collect(protocol.completion, document, position, None)

    assert result is not None
    items = result.items if isinstance(result, CompletionList) else result
    return {item.label: protocol.robot_completion.resolve(protocol.completion, item) for item in items}


def test_named_argument_items_carry_the_argument_description(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    (tmp_path / "DocumentedCompletionLib.py").write_text(LIBRARY, encoding="utf-8")
    suite = tmp_path / "argument_docs.robot"
    suite.write_text(SUITE.format(arguments=""), encoding="utf-8")

    items = _resolved_items(protocol, open_temp_document(suite), Position(line=5, character=len("    Use Integer    ")))

    assert "level=" in items
    assert "base=" in items
    base = items["base="].documentation
    level = items["level="].documentation

    if RF_VERSION >= (6, 1):
        # `int` is documented as `integer`
        assert isinstance(base, MarkupContent)
        assert "integer (Standard)" in base.value
    if RF_VERSION >= (7, 5):
        assert isinstance(base, MarkupContent)
        assert base.value.startswith("The base of the number.")
        assert isinstance(level, MarkupContent)
        assert level.value == "The log level to use."
    else:
        assert level is None


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="BuiltIn documents its arguments since RF 7.5")
def test_level_argument_of_builtin_log(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    suite = tmp_path / "log_argument_docs.robot"
    suite.write_text("*** Test Cases ***\nFirst\n    Log    message    \n", encoding="utf-8")

    items = _resolved_items(
        protocol, open_temp_document(suite), Position(line=2, character=len("    Log    message    "))
    )

    level = items["level="].documentation
    assert isinstance(level, MarkupContent)
    assert "The log level to use." in level.value


VALUE_LIBRARY = '''\
from enum import Enum


class Color(Enum):
    """The colors that can be used."""

    RED = 1
    GREEN = 2


def use_flag(flag: bool):
    pass


def use_color(color: Color):
    pass
'''

ALIAS_VALUE_LIBRARY = (
    VALUE_LIBRARY
    + """

type Shade = Color


def use_shade(shade: Shade):
    pass
"""
)

VALUE_SUITE = """\
*** Settings ***
Library    {library}

*** Test Cases ***
First
    {keyword}    {arguments}
"""


def _value_items(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
    library: str,
    keyword: str,
) -> Dict[str, CompletionItem]:
    name = "AliasValueLib.py" if library is ALIAS_VALUE_LIBRARY else "ValueLib.py"
    (tmp_path / name).write_text(library, encoding="utf-8")
    suite = tmp_path / f"{keyword.replace(' ', '_').lower()}.robot"
    suite.write_text(VALUE_SUITE.format(library=name, keyword=keyword, arguments=""), encoding="utf-8")

    return _resolved_items(protocol, open_temp_document(suite), Position(line=5, character=len(f"    {keyword}    ")))


@pytest.mark.skipif(RF_VERSION < (6, 1), reason="type documentation is collected since RF 6.1")
def test_values_of_boolean_and_enum_arguments_are_offered(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    flag_items = _value_items(protocol, open_temp_document, tmp_path, VALUE_LIBRARY, "Use Flag")
    assert [i for i in flag_items.values() if (i.detail or "").startswith("boolean(")]

    color_items = _value_items(protocol, open_temp_document, tmp_path, VALUE_LIBRARY, "Use Color")
    assert {"RED", "GREEN"} <= set(color_items)


@pytest.mark.skipif(
    sys.version_info < (3, 12) or RF_VERSION < (7, 5),
    reason="needs the `type` statement (Python 3.12) and type alias support (RF 7.5)",
)
def test_values_of_an_aliased_enum_are_offered(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    items = _value_items(protocol, open_temp_document, tmp_path, ALIAS_VALUE_LIBRARY, "Use Shade")

    assert {"RED", "GREEN"} <= set(items)
    documentation = items["RED"].documentation
    assert isinstance(documentation, MarkupContent)
    assert "The colors that can be used." in documentation.value


# --------------------------------------------------------------------------
# Links to the Documentation Viewer
# --------------------------------------------------------------------------

LINKS_LIBRARY = '''\
from enum import Enum

ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"


class Color(Enum):
    """The colors, see [usage](#usage)."""

    RED = 1


def use_integer(base: int, color: Color = Color.RED):
    """Uses an integer.

    Args:
        base: The base of the number, see [Other Keyword].
    """


def other_keyword():
    """Another keyword."""
'''

# the last line, four spaces, is where keywords are completed
KEYWORD_SUITE = "*** Settings ***\nLibrary    Collections\n\n*** Test Cases ***\nFirst\n    \n"


@pytest.fixture
def links_on(protocol: RobotLanguageServerProtocol, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(protocol.robot_initialization_options, "documentation_viewer_links", True)


def _resolved_item(
    protocol: RobotLanguageServerProtocol, document: TextDocument, position: Position, label: str
) -> CompletionItem:
    result = protocol.robot_completion.collect(protocol.completion, document, position, None)

    assert result is not None
    items = result.items if isinstance(result, CompletionList) else result
    item = next((i for i in items if i.label == label), None)
    assert item is not None, f"no item {label!r}"
    return protocol.robot_completion.resolve(protocol.completion, item)


def _documentation(item: CompletionItem) -> str:
    assert isinstance(item.documentation, MarkupContent)
    return item.documentation.value


@pytest.mark.usefixtures("links_on")
def test_keyword_and_library_items_link_to_the_documentation_viewer(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    suite = tmp_path / "keyword_links.robot"
    suite.write_text(KEYWORD_SUITE, encoding="utf-8")
    document = open_temp_document(suite)
    position = Position(line=5, character=4)

    log = _documentation(_resolved_item(protocol, document, position, "Log"))
    collections = _documentation(_resolved_item(protocol, document, position, "Collections"))

    heading = heading_target(log)
    assert heading is not None
    assert (heading["name"], heading.get("keyword")) == ("BuiltIn", "Log")
    if RF_VERSION >= (7, 5):
        assert viewer_link(log, "Set Log Level").get("keyword") == "Set Log Level"
    heading = heading_target(collections)
    assert heading is not None
    assert (heading["name"], heading["args"], heading.get("keyword")) == ("Collections", [], None)


@pytest.mark.usefixtures("links_on")
def test_library_name_in_an_import_links_to_the_documentation_viewer(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    suite = tmp_path / "library_name_links.robot"
    suite.write_text("*** Settings ***\nLibrary    \n", encoding="utf-8")

    xml = _documentation(_resolved_item(protocol, open_temp_document(suite), Position(line=1, character=11), "XML"))

    heading = heading_target(xml)
    assert heading is not None
    assert (heading["name"], heading["args"], heading.get("keyword")) == ("XML", [], None)
    toc_entry = viewer_link(xml, "Parsing XML")
    assert (toc_entry["name"], toc_entry.get("anchor")) == ("XML", "parsing-xml")


@pytest.mark.skipif(RF_VERSION < (7, 5), reason="argument descriptions are parsed since RF 7.5")
@pytest.mark.usefixtures("links_on")
def test_named_argument_and_value_items_link_to_the_documentation_viewer(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    (tmp_path / "LinksCompletionLib.py").write_text(LINKS_LIBRARY, encoding="utf-8")
    suite = tmp_path / "argument_links.robot"
    suite.write_text(
        VALUE_SUITE.format(library="LinksCompletionLib.py", keyword="Use Integer", arguments="1    "), encoding="utf-8"
    )
    document = open_temp_document(suite)

    base = _documentation(
        _resolved_item(protocol, document, Position(line=5, character=len("    Use Integer    ")), "base=")
    )
    red = _documentation(
        _resolved_item(protocol, document, Position(line=5, character=len("    Use Integer    1    ")), "RED")
    )

    for text, keyword, anchor in ((base, "Other Keyword", None), (red, None, "usage")):
        target = viewer_link(text, keyword or anchor or "")
        assert target["name"] == "LinksCompletionLib.py"
        assert Path(target["baseDir"]).resolve() == tmp_path.resolve()
        assert (target.get("keyword"), target.get("anchor")) == (keyword, anchor)


@pytest.mark.usefixtures("links_on")
def test_file_of_a_variables_import_has_no_links(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    (tmp_path / "completion_vars.py").write_text('"""Variables, see [usage](#usage)."""\n\nX = 1\n', encoding="utf-8")
    suite = tmp_path / "variables_links.robot"
    suite.write_text("*** Settings ***\nVariables    \n", encoding="utf-8")

    item = _resolved_item(protocol, open_temp_document(suite), Position(line=1, character=13), "completion_vars.py")

    # resolved like a library, as before, but without a page in the viewer
    documentation = _documentation(item)
    assert "command:" not in documentation
    assert "](#" not in documentation


def test_documentation_without_the_option_is_unchanged(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
) -> None:
    suite = tmp_path / "keyword_no_links.robot"
    suite.write_text(KEYWORD_SUITE, encoding="utf-8")
    document = open_temp_document(suite)
    position = Position(line=5, character=4)
    namespace = protocol.documents_cache.get_namespace(document)
    log = namespace.find_keyword("Log")
    assert log is not None

    assert _documentation(_resolved_item(protocol, document, position, "Log")) == log.to_markdown()
    assert _documentation(_resolved_item(protocol, document, position, "Collections")) == namespace.libraries[
        "Collections"
    ].library_doc.to_markdown(False)
