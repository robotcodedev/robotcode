"""Statements that set a variable that already exists: `EXCEPT AS` and item assignments.

Every scenario of the `variable-assignments` spec runs on both analysis paths:
the legacy path (flag off) and the semantic model (flag on).
"""

import itertools
from pathlib import Path
from typing import Any, Iterator, List, Set, Tuple

import pytest

from robotcode.core.lsp.types import (
    ClientCapabilities,
    InitializedParams,
    InitializeParamsClientInfoType,
    Position,
    ReferenceContext,
    WorkspaceFolder,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.dataclasses import as_dict
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import AnalysisConfig, RobotCodeConfig
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer
from robotcode.robot.utils import RF_VERSION

requires_items = pytest.mark.skipif(RF_VERSION < (6, 1), reason="item assignments need Robot Framework 6.1")

_file_counter = itertools.count()

Place = Tuple[int, int, int]
"""Line (1-based), start and end column of a location."""


@pytest.fixture(scope="module", params=[False, True], ids=["legacy", "model"])
def protocol(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    root = tmp_path_factory.mktemp("variable_assignments")
    # outside the workspace, so the workspace scan at startup never reads a file while it is written
    files = tmp_path_factory.mktemp("variable_assignments_files")
    protocol = RobotLanguageServerProtocol(RobotLanguageServer())
    protocol._initialize(
        ClientCapabilities(),
        root_path=str(root),
        root_uri=root.as_uri(),
        workspace_folders=[WorkspaceFolder(name="test workspace", uri=root.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
    )
    settings: dict[str, Any] = {
        RobotCodeConfig.__config_section__: as_dict(
            RobotCodeConfig(analysis=AnalysisConfig(diagnostic_mode=DiagnosticsMode.OFF)), encode=False
        )
    }
    if request.param:
        settings[RobotCodeConfig.__config_section__]["experimental"] = {"semantic_model": True}
    protocol.workspace.settings = settings

    protocol._initialized(InitializedParams())
    assert protocol.diagnostics.workspace_analyzed_event.wait(300), "the workspace analysis did not end"
    try:
        yield protocol, files, request.param
    finally:
        protocol._shutdown()


def _open(protocol: Any, text: str) -> TextDocument:
    lsp, files, semantic_model = protocol
    path = Path(files, f"test_{next(_file_counter)}.robot")
    path.write_text(text, encoding="utf-8")
    document: TextDocument = lsp.documents.get_or_open_document(path, "robotframework")
    assert (lsp.documents_cache.get_namespace(document).semantic_model is not None) == semantic_model
    return document


# the position of `word` in the first line of the document that contains `line_text`
def _position(document: TextDocument, line_text: str, word: str) -> Position:
    for line, text in enumerate(document.text().splitlines()):
        if line_text in text:
            return Position(line=line, character=text.index(word, text.index(line_text)))
    raise AssertionError(f"no line contains {line_text!r}")


def _place(document: TextDocument, line_text: str, word: str) -> Place:
    position = _position(document, line_text, word)
    return (position.line + 1, position.character, position.character + len(word))


def _references(protocol: Any, document: TextDocument, position: Position) -> Set[Place]:
    lsp = protocol[0]
    result = lsp.robot_references.collect(
        lsp.robot_references, document, position, ReferenceContext(include_declaration=True)
    )
    return {(r.range.start.line + 1, r.range.start.character, r.range.end.character) for r in result or []}


def _renamed(protocol: Any, document: TextDocument, position: Position, new_name: str) -> Set[Place]:
    edit = protocol[0].robot_rename.collect(None, document, position, new_name)
    assert edit is not None
    return {
        (e.range.start.line + 1, e.range.start.character, e.range.end.character)
        for change in edit.document_changes or []
        for e in change.edits
    }


def _not_found(protocol: Any, document: TextDocument) -> List[Place]:
    namespace = protocol[0].documents_cache.get_namespace(document)
    return sorted(
        (d.range.start.line + 1, d.range.start.character, d.range.end.character)
        for d in namespace.diagnostics
        if d.code == "VariableNotFound"
    )


_EXCEPT_ARGUMENT = """\
*** Test Cases ***
Test
    Keyword    x

*** Keywords ***
Keyword
    [Arguments]    ${error}
    TRY
        Fail    boom
    EXCEPT    AS    ${error}
        No Operation
    END
    Log    ${error}
"""


def test_except_as_with_the_name_of_an_argument(protocol: Any) -> None:
    document = _open(protocol, _EXCEPT_ARGUMENT)
    except_as = _place(document, "EXCEPT    AS    ${error}", "error")
    argument = _position(document, "[Arguments]    ${error}", "error")

    assert except_as in _references(protocol, document, argument)
    assert except_as in _renamed(protocol, document, argument, "failure")


def test_except_as_with_the_name_of_a_local_variable(protocol: Any) -> None:
    document = _open(
        protocol,
        "*** Test Cases ***\nTest\n    ${err}=    Set Variable    before\n"
        "    TRY\n        Fail    boom\n    EXCEPT    AS    ${err}\n        No Operation\n    END\n",
    )

    references = _references(protocol, document, _position(document, "${err}=    Set Variable", "err"))

    assert _place(document, "EXCEPT    AS    ${err}", "err") in references


def test_except_as_with_a_new_name(protocol: Any) -> None:
    document = _open(
        protocol,
        "*** Test Cases ***\nTest\n    TRY\n        Fail    boom\n    EXCEPT    AS    ${err}\n        Log    ${err}\n"
        "    END\n",
    )

    references = _references(protocol, document, _position(document, "Log    ${err}", "err"))

    # the name in EXCEPT AS is the declaration of a new local variable
    assert references == {_place(document, "EXCEPT    AS    ${err}", "err"), _place(document, "Log    ${err}", "err")}


@requires_items
def test_item_assignment_to_a_list_argument(protocol: Any) -> None:
    document = _open(
        protocol,
        "*** Test Cases ***\nTest\n    Keyword    a    b\n\n*** Keywords ***\nKeyword\n"
        "    [Arguments]    @{items}\n    ${items}[0]=    Set Variable    x\n    Log Many    @{items}\n",
    )
    assignment = _place(document, "${items}[0]=", "items")
    argument = _position(document, "[Arguments]    @{items}", "items")

    assert assignment in _references(protocol, document, argument)
    assert assignment in _renamed(protocol, document, argument, "values")


@requires_items
def test_item_assignment_to_a_suite_variable(protocol: Any) -> None:
    document = _open(
        protocol,
        "*** Variables ***\n&{SUITE_DICT}    k=v\n\n*** Test Cases ***\nTest\n"
        "    ${SUITE_DICT}[k]=    Set Variable    x\n",
    )

    references = _references(protocol, document, _position(document, "&{SUITE_DICT}", "SUITE_DICT"))

    assert _place(document, "${SUITE_DICT}[k]=", "SUITE_DICT") in references


@requires_items
def test_known_variable_in_the_index(protocol: Any) -> None:
    document = _open(
        protocol,
        "*** Test Cases ***\nTest\n    ${key}=    Set Variable    k\n    ${d}=    Create Dictionary\n"
        "    ${d}[${key}]=    Set Variable    v\n",
    )

    references = _references(protocol, document, _position(document, "${key}=    Set Variable", "key"))

    assert _place(document, "${d}[${key}]=", "key") in references


@requires_items
def test_unknown_variables(protocol: Any) -> None:
    document = _open(
        protocol,
        "*** Test Cases ***\nTest\n    ${UNKNOWN}[0]=    Set Variable    x\n    ${d}=    Create Dictionary\n"
        "    ${d}[${missing}]=    Set Variable    v\n",
    )

    assert _not_found(protocol, document) == [
        _place(document, "${UNKNOWN}[0]=", "UNKNOWN"),
        _place(document, "${d}[${missing}]=", "missing"),
    ]
