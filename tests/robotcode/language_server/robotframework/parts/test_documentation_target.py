"""Tests for the target of the documentation actions and of the Keywords view."""

import urllib.parse
from pathlib import Path
from typing import Callable, Dict, List

import pytest

from robotcode.core.lsp.types import (
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    CodeActionTriggerKind,
    Position,
    Range,
    TextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.parts.code_action_documentation import DocumentationTarget
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

SUITE = """\
*** Settings ***
Library     Collections
Library     ./arglib.py    a_param=from hello    WITH NAME    lib_hello
Library     ./arglib.py    a_param=${LIB_ARG}    WITH NAME    lib_var
Resource    sub/local.resource

*** Variables ***
${LIB_ARG}    from lib

*** Test Cases ***
First
    Nested Keyword
    Local Lib Keyword
    Other Keyword
    Log    hello
    lib_hello.Arg Keyword
    lib_var.Arg Keyword
    Arg Keyword
"""

LOCAL_RESOURCE = """\
*** Settings ***
Resource    deeper/nested.resource
Resource    ${CURDIR}/other.resource
Library     ./local_lib.py

*** Keywords ***
Local Keyword
    No Operation
"""

NESTED_RESOURCE = """\
*** Keywords ***
Nested Keyword
    No Operation
"""

OTHER_RESOURCE = """\
*** Keywords ***
Other Keyword
    No Operation
"""

LOCAL_LIB = """\
def local_lib_keyword():
    pass
"""

ARGLIB = """\
class arglib:
    def __init__(self, a_param=None):
        self.a_param = a_param

    def arg_keyword(self):
        return self.a_param
"""

SUITE_WITH_KEYWORDS = """\
*** Test Cases ***
First
    My Suite Keyword

*** Keywords ***
My Suite Keyword
    No Operation
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    files = {
        "suite.robot": SUITE,
        "sub/local.resource": LOCAL_RESOURCE,
        "sub/deeper/nested.resource": NESTED_RESOURCE,
        "sub/other.resource": OTHER_RESOURCE,
        "sub/local_lib.py": LOCAL_LIB,
        "arglib.py": ARGLIB,
        "with_keywords.robot": SUITE_WITH_KEYWORDS,
    }
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def _position(document: TextDocument, line_text: str) -> Position:
    for line, text in enumerate(document.text().splitlines()):
        if text.strip() == line_text:
            return Position(line=line, character=text.index(line_text))
    raise AssertionError(f"line {line_text!r} not found")


def _actions(protocol: RobotLanguageServerProtocol, document: TextDocument, position: Position) -> List[CodeAction]:
    result = protocol.robot_code_action_documentation.collect(
        protocol.robot_code_action_documentation,
        document,
        Range(position, position),
        CodeActionContext(
            diagnostics=[],
            only=[CodeActionKind.SOURCE.value],
            trigger_kind=CodeActionTriggerKind.INVOKED,
        ),
    )
    assert result is not None
    return [a for a in result if isinstance(a, CodeAction)]


def _target(actions: List[CodeAction]) -> DocumentationTarget:
    action = next(a for a in actions if a.title == "Show in Documentation Viewer")
    assert action.command is not None
    assert action.command.command == "robotcode.showInDocumentationViewer"
    assert action.command.arguments is not None
    target = action.command.arguments[0]
    assert isinstance(target, DocumentationTarget)
    return target


def _url(actions: List[CodeAction]) -> str:
    action = next(a for a in actions if a.title == "Open Documentation")
    assert action.command is not None
    assert action.command.arguments is not None
    return str(action.command.arguments[0])


def _query(url: str) -> Dict[str, str]:
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(url).query, keep_blank_values=True).items()}


def _same_path(path: str, expected: Path) -> bool:
    return Path(path).resolve() == expected.resolve()


@pytest.mark.parametrize(
    ("call", "name", "keyword"),
    [
        ("Nested Keyword", "deeper/nested.resource", "Nested Keyword"),
        ("Local Lib Keyword", "./local_lib.py", "Local Lib Keyword"),
    ],
)
def test_keyword_of_an_import_of_a_resource_in_another_directory(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
    call: str,
    name: str,
    keyword: str,
) -> None:
    document = open_temp_document(project / "suite.robot")

    actions = _actions(protocol, document, _position(document, call))
    target = _target(actions)

    assert target.name == name
    assert target.keyword == keyword
    assert target.base_dir is not None
    assert _same_path(target.base_dir, project / "sub")
    # outside the workspace folder, so the URL keeps the directory absolute
    assert _same_path(_query(_url(actions))["basedir"], project / "sub")


def test_curdir_is_the_directory_of_the_importing_file(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
) -> None:
    document = open_temp_document(project / "suite.robot")

    target = _target(_actions(protocol, document, _position(document, "Other Keyword")))

    assert _same_path(target.name, project / "sub" / "other.resource")
    assert target.base_dir is None
    assert target.keyword == "Other Keyword"


def test_libraries_imported_by_name_have_no_base_dir(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
) -> None:
    document = open_temp_document(project / "suite.robot")

    position = _position(document, "Library     Collections")
    collections = _target(_actions(protocol, document, Position(line=position.line, character=14)))
    log = _target(_actions(protocol, document, _position(document, "Log    hello")))

    assert (collections.name, collections.args, collections.base_dir, collections.keyword) == (
        "Collections",
        [],
        None,
        None,
    )
    assert (log.name, log.args, log.base_dir, log.keyword) == ("BuiltIn", [], None, "Log")


@pytest.mark.parametrize(
    ("file", "header"),
    [
        ("sub/local.resource", "Local Keyword"),
        ("with_keywords.robot", "My Suite Keyword"),
    ],
)
def test_keyword_definition_header_targets_its_file(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
    file: str,
    header: str,
) -> None:
    path = project / file
    document = open_temp_document(path)

    actions = _actions(protocol, document, _position(document, header))
    target = _target(actions)

    assert {a.title for a in actions} == {
        "Open Documentation",
        "Show in Documentation Viewer",
        "Show in New Documentation Viewer",
    }
    new_viewer = next(a for a in actions if a.title == "Show in New Documentation Viewer")
    assert new_viewer.command is not None
    assert new_viewer.command.command == "robotcode.showInNewDocumentationViewer"
    assert new_viewer.command.arguments == [target]
    assert target.name == path.name
    assert target.keyword == header
    assert target.base_dir is not None
    assert _same_path(target.base_dir, path.parent)


@pytest.mark.parametrize(
    ("call", "args"),
    [
        ("lib_hello.Arg Keyword", ["a_param=from hello"]),
        ("lib_var.Arg Keyword", ["a_param=from lib"]),
    ],
)
def test_prefixed_call_uses_the_arguments_of_its_import(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
    call: str,
    args: List[str],
) -> None:
    document = open_temp_document(project / "suite.robot")

    actions = _actions(protocol, document, _position(document, call))
    target = _target(actions)

    assert target.name == "./arglib.py"
    assert target.args == args
    assert target.keyword == "Arg Keyword"
    assert _query(_url(actions))["args"] == "::".join(args)


def test_call_without_prefix_uses_the_import_of_the_search_order(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    imports_manager = protocol.documents_cache.get_imports_manager_for_uri(Uri.from_path(project / "suite.robot"))
    monkeypatch.setattr(imports_manager, "global_library_search_order", ["lib_var"])
    document = open_temp_document(project / "suite.robot")

    actions = _actions(protocol, document, _position(document, "Arg Keyword"))
    target = _target(actions)

    assert (target.name, target.args, target.keyword) == ("./arglib.py", ["a_param=from lib"], "Arg Keyword")
    assert _query(_url(actions))["args"] == "a_param=from lib"


@pytest.mark.parametrize(
    ("file", "keyword"),
    [
        ("sub/local.resource", "Local Keyword"),
        ("with_keywords.robot", "My Suite Keyword"),
    ],
)
def test_keywords_view_local_keyword(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
    file: str,
    keyword: str,
) -> None:
    path = project / file
    document = open_temp_document(path)
    text_document = TextDocumentIdentifier(uri=str(document.uri))
    keywords_view = protocol.robot_keywords_treeview

    keywords = keywords_view._get_document_keywords(text_document)
    assert keywords is not None
    keyword_id = next(k.id for k in keywords if k.name == keyword)

    target = keywords_view._get_documentation_target(text_document, None, keyword_id)
    assert target is not None
    assert target.name == path.name
    assert target.keyword == keyword
    assert target.base_dir is not None
    assert _same_path(target.base_dir, path.parent)

    # the bare id, as the Keywords view sends it for the document's own keywords
    url = keywords_view._get_documentation_url(text_document, None, keyword_id)
    assert url is not None
    assert url.endswith(f"#{keyword}")


def test_keywords_view_imports(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
) -> None:
    document = open_temp_document(project / "suite.robot")
    text_document = TextDocumentIdentifier(uri=str(document.uri))
    keywords_view = protocol.robot_keywords_treeview

    imports = keywords_view._get_document_imports(text_document)
    assert imports is not None

    lib_var = next(i for i in imports if i.alias == "lib_var")
    target = keywords_view._get_documentation_target(text_document, lib_var.id, None)
    assert target is not None
    assert (target.name, target.args, target.keyword) == ("./arglib.py", ["a_param=from lib"], None)

    nested = next(i for i in imports if i.keywords and any(k.name == "Nested Keyword" for k in i.keywords))
    url = keywords_view._get_documentation_url(text_document, nested.id, None)
    assert url is not None
    assert _same_path(_query(url)["basedir"], project / "sub")


def test_keywords_view_unknown_id(
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    project: Path,
) -> None:
    document = open_temp_document(project / "suite.robot")
    text_document = TextDocumentIdentifier(uri=str(document.uri))

    assert protocol.robot_keywords_treeview._get_documentation_target(text_document, "unknown", None) is None
