"""Tests for the links to the Documentation Viewer in signature help."""

from pathlib import Path
from typing import Callable, List, Optional

import pytest

from robotcode.core.lsp.types import MarkupContent, Position, SignatureHelp
from robotcode.core.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.utils import RF_VERSION
from tests.robotcode.language_server.robotframework.tools import write_project
from tests.robotcode.language_server.robotframework.viewer_links import viewer_link, viewer_links

SUITE = """\
*** Settings ***
Library     ./arglib.py    a_param=from hello    WITH NAME    lib_hello
Library     ./arglib.py    a_param=${LIB_ARG}    WITH NAME    lib_var
Library     ./faillib.py    port=80x
Variables   ./sigvars.py    some_arg

*** Variables ***
${LIB_ARG}    from lib

*** Test Cases ***
First
    Log    hello
    lib_hello.Arg Keyword    x
    lib_var.Arg Keyword    x
    My Keyword    x
    Run Keyword If    ${TRUE}    lib_var.Arg Keyword    x

*** Keywords ***
My Keyword
    [Documentation]    Calls `Other Keyword`.
    [Arguments]    ${value}
    No Operation

Other Keyword
    No Operation
"""

ARGLIB = '''\
class arglib:
    def __init__(self, a_param=None):
        """Creates the library. See `Arg Keyword`."""
        self.a_param = a_param

    def arg_keyword(self, value=None):
        """Returns the parameter. See `Other Arg Keyword`."""
        return self.a_param

    def other_arg_keyword(self):
        """Another keyword."""
'''

# `80x` is no integer: RobotCode loads the library without the arguments
FAILLIB = '''\
class faillib:
    def __init__(self, port: int = 8270):
        """Creates the library. See `Connect`."""
        self.port = port

    def connect(self):
        """Connects."""
'''

VARIABLES = '''\
def get_variables(some_arg=None):
    """Variables, see [#usage|usage]."""
    return {"X": some_arg}
'''


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The project of the module's tests, shared by all of them and read-only."""
    return write_project(
        tmp_path_factory.mktemp("project"),
        {
            "arglib.py": ARGLIB,
            "faillib.py": FAILLIB,
            "sigvars.py": VARIABLES,
            "suite.robot": SUITE,
        },
    )


@pytest.fixture
def document(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> TextDocument:
    monkeypatch.setattr(protocol.robot_initialization_options, "documentation_viewer_links", True)
    # both analysis paths: the namespace of the suite gets a semantic model
    monkeypatch.setattr(protocol.documents_cache.analysis_config, "semantic_model", True)
    return open_temp_document(project / "suite.robot")


def _position(document: TextDocument, line_start: str, word: str) -> Position:
    for line, text in enumerate(document.text().splitlines()):
        if text.strip().startswith(line_start):
            return Position(line=line, character=text.rindex(word) + 1)
    raise AssertionError(f"no line starts with {line_start!r}")


def _documentation(signature_help: Optional[SignatureHelp]) -> List[str]:
    """The documentation of the signature and of each of its parameters."""
    assert signature_help is not None
    signature = signature_help.signatures[0]
    parts = [signature.documentation, *(p.documentation for p in signature.parameters or [])]
    return [p.value for p in parts if isinstance(p, MarkupContent)]


def _signature_help(
    protocol: RobotLanguageServerProtocol, document: TextDocument, line_start: str, word: str
) -> List[str]:
    """The documentation of the signature help, the same on both analysis paths."""
    part = protocol.robot_signature_help
    namespace = protocol.documents_cache.get_namespace(document)
    assert namespace.semantic_model is not None
    position = _position(document, line_start, word)

    legacy = part._collect_legacy(document, position, None)
    model = part._collect_from_model(document, position, namespace, namespace.semantic_model)

    assert legacy == model
    return _documentation(model)


@pytest.mark.parametrize(
    ("line_start", "word", "link", "args", "keyword"),
    [
        # the first import, through its prefix
        ("lib_hello.Arg Keyword", "x", "Other Arg Keyword", ["a_param=from hello"], "Other Arg Keyword"),
        # the second import of the same library
        ("lib_var.Arg Keyword", "x", "Other Arg Keyword", ["a_param=from lib"], "Other Arg Keyword"),
        # the arguments of a library import
        (
            "Library     ./arglib.py    a_param=from hello",
            "a_param",
            "Arg Keyword",
            ["a_param=from hello"],
            "Arg Keyword",
        ),
    ],
)
def test_links_of_a_library_keyword(
    protocol: RobotLanguageServerProtocol,
    document: TextDocument,
    project: Path,
    line_start: str,
    word: str,
    link: str,
    args: List[str],
    keyword: str,
) -> None:
    documentation = "\n".join(_signature_help(protocol, document, line_start, word))

    target = viewer_link(documentation, link)
    assert (target["name"], target["args"], target.get("keyword")) == ("./arglib.py", args, keyword)
    assert Path(target["baseDir"]).resolve() == project.resolve()


def test_links_of_a_library_whose_arguments_fail(
    protocol: RobotLanguageServerProtocol, document: TextDocument, project: Path
) -> None:
    documentation = "\n".join(_signature_help(protocol, document, "Library     ./faillib.py", "port"))

    # the signature help shows the library loaded without the arguments, so does the page
    target = viewer_link(documentation, "Connect")
    assert (target["name"], target["args"], target.get("keyword")) == ("./faillib.py", [], "Connect")
    assert Path(target["baseDir"]).resolve() == project.resolve()


def test_links_of_a_builtin_keyword(protocol: RobotLanguageServerProtocol, document: TextDocument) -> None:
    documentation = "\n".join(_signature_help(protocol, document, "Log    hello", "hello"))

    assert {target["name"] for _, target in viewer_links(documentation)} <= {"BuiltIn"}
    if RF_VERSION >= (7, 5):
        assert viewer_link(documentation, "Set Log Level").get("keyword") == "Set Log Level"


def test_links_of_a_keyword_of_the_current_file(
    protocol: RobotLanguageServerProtocol, document: TextDocument, project: Path
) -> None:
    documentation = "\n".join(_signature_help(protocol, document, "My Keyword    x", "x"))

    target = viewer_link(documentation, "Other Keyword")
    assert (target["name"], target.get("keyword")) == ("suite.robot", "Other Keyword")
    assert Path(target["baseDir"]).resolve() == project.resolve()


def test_run_keyword_if_links_to_the_page_of_the_outer_keyword(
    protocol: RobotLanguageServerProtocol, document: TextDocument
) -> None:
    documentation = "\n".join(_signature_help(protocol, document, "Run Keyword If", "x"))

    target = viewer_link(documentation, "Run Keyword")
    assert (target["name"], target.get("keyword")) == ("BuiltIn", "Run Keyword")
    assert {target["name"] for _, target in viewer_links(documentation)} == {"BuiltIn"}


@pytest.mark.skipif(RF_VERSION >= (7, 0), reason="variables files have no signature help since RF 7.0")
def test_variables_import_has_no_links(protocol: RobotLanguageServerProtocol, document: TextDocument) -> None:
    documentation = "\n".join(_signature_help(protocol, document, "Variables   ./sigvars.py", "some_arg"))

    assert "usage" in documentation
    assert "command:" not in documentation
    assert "](#" not in documentation
