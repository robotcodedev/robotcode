"""Tests for the links to the Documentation Viewer in the hover."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

from robotcode.core.lsp.types import MarkupContent, Position
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.utils import RF_VERSION
from tests.robotcode.language_server.robotframework.viewer_links import heading_target, viewer_link, viewer_links

SUITE = """\
*** Settings ***
Documentation    The suite.
...
...    = Usage =
...
...    How to use it.
Library     BuiltIn
Library     Collections
Library     XML
Library     OperatingSystem    WITH NAME    OS
Library     ./arglib.py    a_param=from hello    WITH NAME    lib_hello
Library     ./arglib.py    a_param=${LIB_ARG}    WITH NAME    lib_var
Library     ./htmllib.py
Library     ./mdlib.py
Resource    sub/local.resource
Resource    dup1.resource
Resource    dup2.resource
Variables   vars.py

*** Variables ***
${LIB_ARG}    from lib

*** Test Cases ***
First
    [Documentation]    See [#usage|usage].
    Remove From List    ${LIST}    0
    Collections.Append To List    ${LIST}    1
    lib_var.Arg Keyword
    lib_hello.Arg Keyword
    Local Keyword
    Dup Keyword
    Weird ] Name
    Html Keyword
    Paint    RED
    Log    hello
    Run Keyword If    ${TRUE}    No Operation
    Convert To Integer    1
    Parse Xml    <a/>
    Res Keyword
    Suite Keyword

*** Keywords ***
Suite Keyword
    [Documentation]    See `Usage`, `Introduction` and `Keywords`.
    No Operation
"""

LOCAL_RESOURCE = """\
*** Keywords ***
Local Keyword
    No Operation

Weird ] Name
    No Operation

Res Keyword
    [Documentation]    See `Weird ] Name` and `Local Keyword`.
    No Operation
"""

DUP_RESOURCE = """\
*** Keywords ***
Dup Keyword
    [Documentation]    See [#usage|usage].
    No Operation
"""

ARGLIB = '''\
from robot.api.deco import keyword


class arglib:
    """Use `Arg Keyword` to get the parameter."""

    def __init__(self, a_param=None):
        self.a_param = a_param

    def arg_keyword(self):
        """Returns the parameter. See `Hidden Kw`."""
        return self.a_param

    @keyword(tags=["robot:private"])
    def hidden_kw(self):
        """Not on the page."""
'''

HTMLLIB = '''\
"""<h2>Usage</h2><p>How to use it.</p>"""

ROBOT_LIBRARY_DOC_FORMAT = "HTML"


def html_keyword():
    """See <a href="#usage">usage</a>."""
'''

MDLIB = '''\
from enum import Enum

ROBOT_LIBRARY_DOC_FORMAT = "MARKDOWN"


class Color(Enum):
    """The colors."""

    RED = 1


def color_enum():
    """Another keyword."""


def paint(shade: Color):
    """Paints in [Color]."""
'''


@pytest.fixture
def project(tmp_path: Path) -> Path:
    files = {
        "suite.robot": SUITE,
        "sub/local.resource": LOCAL_RESOURCE,
        "dup1.resource": DUP_RESOURCE,
        "dup2.resource": DUP_RESOURCE,
        "arglib.py": ARGLIB,
        "htmllib.py": HTMLLIB,
        "mdlib.py": MDLIB,
        "vars.py": "X = 1\n",
    }
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


@pytest.fixture
def links_on(protocol: RobotLanguageServerProtocol, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(protocol.robot_initialization_options, "documentation_viewer_links", True)


def _position(document: TextDocument, line_start: str, word: str) -> Position:
    for line, text in enumerate(document.text().splitlines()):
        if text.strip().startswith(line_start):
            return Position(line=line, character=text.index(word, text.index(line_start)) + 1)
    raise AssertionError(f"no line starts with {line_start!r}")


def _hover(
    protocol: RobotLanguageServerProtocol, document: TextDocument, line_start: str, word: Optional[str] = None
) -> str:
    position = _position(document, line_start, word or line_start)
    result = protocol.robot_hover.collect(protocol.robot_hover, document, position)
    assert result is not None
    assert isinstance(result.contents, MarkupContent)
    return result.contents.value


def _check(
    target: Optional[Dict[str, Any]],
    document: TextDocument,
    name: str,
    *,
    args: Optional[List[str]] = None,
    base_dir: Optional[Path] = None,
    keyword: Optional[str] = None,
    anchor: Optional[str] = None,
    data_type: Optional[str] = None,
) -> None:
    assert target is not None
    assert target["uri"] == str(document.uri)
    assert target["name"] == name
    assert target["args"] == (args or [])
    if base_dir is None:
        assert "baseDir" not in target
    else:
        assert Path(target["baseDir"]).resolve() == base_dir.resolve()
    assert target.get("keyword") == keyword
    assert target.get("anchor") == anchor
    assert target.get("dataType") == data_type


@pytest.mark.usefixtures("links_on")
class TestHeadingLink:
    def test_keyword_call(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Remove From List")

        assert hover.startswith("### [Keyword *Remove From List*](command:")
        _check(heading_target(hover), document, "Collections", keyword="Remove From List")

    def test_keyword_definition(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "sub" / "local.resource")

        hover = _hover(protocol, document, "Local Keyword")

        _check(heading_target(hover), document, "local.resource", base_dir=project / "sub", keyword="Local Keyword")

    def test_library_import(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Library     Collections", "Collections")

        assert hover.startswith("### [Library *Collections*](command:")
        _check(heading_target(hover), document, "Collections")

    @pytest.mark.parametrize(
        ("line_start", "args"),
        [
            ("Library     ./arglib.py    a_param=from hello", ["a_param=from hello"]),
            # the name of the second import is a reference of the first import
            ("Library     ./arglib.py    a_param=${LIB_ARG}", ["a_param=from lib"]),
        ],
    )
    def test_library_import_with_arguments(
        self,
        protocol: RobotLanguageServerProtocol,
        open_temp_document: Callable[[Path], TextDocument],
        project: Path,
        line_start: str,
        args: List[str],
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, line_start, "./arglib.py")

        # the heading of the library's initializer comes first
        assert "#### Arguments" in hover.split("\n---\n", 1)[0]
        _check(heading_target(hover), document, "./arglib.py", args=args, base_dir=project)

    def test_resource_import(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Resource    sub/local.resource", "sub/local.resource")

        _check(heading_target(hover), document, "sub/local.resource", base_dir=project)

    def test_keyword_of_the_second_import(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "lib_var.Arg Keyword", "Arg Keyword")

        _check(
            heading_target(hover),
            document,
            "./arglib.py",
            args=["a_param=from lib"],
            base_dir=project,
            keyword="Arg Keyword",
        )

    def test_alias(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Library     OperatingSystem", "OS")

        assert hover.startswith("### [Library *OperatingSystem*](command:")
        _check(heading_target(hover), document, "OperatingSystem")

    def test_prefix(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Collections.Append To List", "Collections")

        assert hover.startswith("### [Library *Collections*](command:")
        _check(heading_target(hover), document, "Collections")

    def test_keyword_with_a_bracket_in_its_name(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Weird ] Name")

        assert hover.startswith("### [Keyword *Weird \\] Name*](command:")
        _check(heading_target(hover), document, "sub/local.resource", base_dir=project, keyword="Weird ] Name")

    def test_variables_import_has_no_link(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Variables   vars.py", "vars.py")

        assert "command:" not in hover

    def test_call_of_several_keywords_has_no_link(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Dup Keyword")

        assert hover.count("### Keyword *Dup Keyword*") == 2
        assert "command:" not in hover
        # a link to a place in the documentation itself is text
        assert hover.count("See usage.") == 2
        assert "](#" not in hover


def test_without_the_option_the_hover_has_no_links(
    protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
) -> None:
    document = open_temp_document(project / "suite.robot")

    assert "command:" not in _hover(protocol, document, "Remove From List")
    assert "command:" not in _hover(protocol, document, "Library     BuiltIn", "BuiltIn")


@pytest.mark.usefixtures("links_on")
class TestLinksInTheDocumentation:
    def test_table_of_contents_of_builtin(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Library     BuiltIn", "BuiltIn")

        _check(viewer_link(hover, "Evaluating expressions"), document, "BuiltIn", anchor="evaluating-expressions")
        assert "](#" not in hover

    def test_link_of_the_author_in_html(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Html Keyword")

        _check(viewer_link(hover, "usage"), document, "./htmllib.py", base_dir=project, anchor="usage")
        assert 'href="#' not in hover

    def test_test_case_shows_links_as_text(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "First")

        assert "See usage." in hover
        assert "](#" not in hover
        assert "command:" not in hover

    def test_names_in_a_robot_format_library_hover(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Library     ./arglib.py    a_param=from hello", "./arglib.py")

        _check(
            viewer_link(hover, "Arg Keyword"),
            document,
            "./arglib.py",
            args=["a_param=from hello"],
            base_dir=project,
            keyword="Arg Keyword",
        )

    @pytest.mark.skipif(RF_VERSION < (6, 0), reason="robot:private exists since RF 6.0")
    def test_private_keyword_stays_code(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "lib_hello.Arg Keyword", "Arg Keyword")

        assert "See `Hidden Kw`." in hover
        assert [text for text, _ in viewer_links(hover)] == ["Keyword *Arg Keyword*"]

    @pytest.mark.skipif(RF_VERSION < (7, 5), reason="the documentation of Log names them since RF 7.5")
    def test_keyword_and_section_named_in_markdown(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Log    hello", "Log")

        _check(viewer_link(hover, "Set Log Level"), document, "BuiltIn", keyword="Set Log Level")
        _check(viewer_link(hover, "String representations"), document, "BuiltIn", anchor="string-representations")

    def test_keyword_named_in_the_robot_format(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Run Keyword If")

        _check(viewer_link(hover, "Run Keyword"), document, "BuiltIn", keyword="Run Keyword")

    @pytest.mark.skipif(RF_VERSION < (7, 5), reason="the standard libraries document these types since RF 7.5")
    def test_argument_and_return_types(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        convert = _hover(protocol, document, "Convert To Integer")
        parse_xml = _hover(protocol, document, "Parse Xml")

        _check(viewer_link(convert, "`int`"), document, "BuiltIn", data_type="integer")
        assert "**Return Type**: [`Element`](command:" in parse_xml
        _check(viewer_link(parse_xml, "`Element`"), document, "XML", data_type="Element")

    @pytest.mark.skipif(RF_VERSION < (6, 1), reason="type documentation is collected since RF 6.1")
    def test_type_whose_heading_has_a_numbered_anchor(
        self, protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
    ) -> None:
        document = open_temp_document(project / "suite.robot")

        hover = _hover(protocol, document, "Paint")

        # the type, not the keyword `Color Enum`; the viewer knows the anchor of its heading
        _check(viewer_link(hover, "`Color`"), document, "./mdlib.py", base_dir=project, data_type="Color")
        _check(viewer_link(hover, "Color"), document, "./mdlib.py", base_dir=project, data_type="Color")


@pytest.mark.usefixtures("links_on")
def test_escaped_link_text_in_a_resource_keyword(
    protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
) -> None:
    """Without a variable in the documentation, its backslashes are not doubled, the link text stays escaped."""
    document = open_temp_document(project / "suite.robot")

    hover = _hover(protocol, document, "Res Keyword")

    _check(
        viewer_link(hover, "Weird \\] Name"),
        document,
        "sub/local.resource",
        base_dir=project,
        keyword="Weird ] Name",
    )
    assert "\\\\" not in hover


@pytest.mark.usefixtures("links_on")
def test_keyword_of_a_suite_links_no_sections_of_its_documentation(
    protocol: RobotLanguageServerProtocol, open_temp_document: Callable[[Path], TextDocument], project: Path
) -> None:
    """`robotcode doc lib` documents a suite file without its documentation."""
    document = open_temp_document(project / "suite.robot")

    hover = _hover(protocol, document, "Suite Keyword")

    assert "See `Usage`, `Introduction` and " in hover
    _check(viewer_link(hover, "Keywords"), document, "suite.robot", base_dir=project, anchor="keywords")
