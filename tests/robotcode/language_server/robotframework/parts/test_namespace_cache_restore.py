"""Tests for the references to imports of a namespace restored from the namespace disk cache.

A suite is opened, closed and opened again. The first time its namespace is
analyzed fresh and stored in the cache; the second time it is restored from
there. Both namespaces must have the same entries in `namespace_references`,
also when the suite imports something that is already loaded implicitly or
through a resource file.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest
from pytest_mock import MockerFixture

from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.diagnostics.namespace import Namespace
from tests.robotcode.language_server.robotframework.tools import write_project

ARGLIB = """\
class arglib:
    def __init__(self, p=None):
        self.p = p

    def arg_keyword(self):
        return self.p
"""

CASES: Dict[str, Dict[str, str]] = {
    "explicit BuiltIn": {
        "suite.robot": """\
*** Settings ***
Library     BuiltIn

*** Test Cases ***
First
    Log    hello
""",
    },
    "explicit BuiltIn and a call with its prefix": {
        "suite.robot": """\
*** Settings ***
Library     BuiltIn

*** Test Cases ***
First
    BuiltIn.Log    hello
""",
    },
    "library after a resource file that imports it": {
        "lib.resource": """\
*** Settings ***
Library     Collections
""",
        "suite.robot": """\
*** Settings ***
Resource    lib.resource
Library     Collections

*** Test Cases ***
First
    Collections.Log List    ${{[]}}
""",
    },
    "variable file after a resource file that imports it": {
        "vars.py": "X = 1\n",
        "lib.resource": """\
*** Settings ***
Variables    vars.py
""",
        "suite.robot": """\
*** Settings ***
Resource     lib.resource
Variables    vars.py

*** Test Cases ***
First
    Log    ${X}
""",
    },
    "library with other arguments than in a resource file": {
        "arglib.py": ARGLIB,
        "lib.resource": """\
*** Settings ***
Library     ./arglib.py    a
""",
        "suite.robot": """\
*** Settings ***
Resource    lib.resource
Library     ./arglib.py    b

*** Test Cases ***
First
    Arg Keyword
""",
    },
}

# a referencing location: file name, line, character
Reference = Tuple[str, int, int]

# an entry of `namespace_references`: class, name, arguments, alias, importing file,
# import range (start line, start character), and the referencing locations
Entry = Tuple[str, str, Tuple[str, ...], Optional[str], Optional[str], Tuple[int, int], Tuple[Reference, ...]]


def _references_to_imports(protocol: RobotLanguageServerProtocol, document: TextDocument) -> List[Entry]:
    namespace = protocol.documents_cache.get_namespace(document)
    entries: List[Entry] = [
        (
            type(entry).__name__,
            entry.name,
            tuple(str(a) for a in entry.args),
            entry.alias,
            Path(entry.import_source).name if entry.import_source else None,
            (entry.import_range.start.line, entry.import_range.start.character),
            tuple(
                sorted(
                    (Uri(location.uri).to_path().name, location.range.start.line, location.range.start.character)
                    for location in locations
                )
            ),
        )
        for entry, locations in namespace.namespace_references.items()
    ]
    # the alias and the importing file can be None
    return sorted(entries, key=repr)


def _close_project(protocol: RobotLanguageServerProtocol, project: Path) -> None:
    for document in list(protocol.documents.documents):
        if project in document.uri.to_path().parents:
            protocol.documents_cache.get_project_index(document).remove_file(str(document.uri.to_path()))
            protocol.documents.close_document(document, real_close=True)


@pytest.mark.parametrize("semantic_model", [False, True], ids=["legacy", "model"])
@pytest.mark.parametrize("case", list(CASES))
def test_restored_references_to_imports_match_the_fresh_analysis(
    protocol: RobotLanguageServerProtocol,
    tmp_path: Path,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    semantic_model: bool,
) -> None:
    monkeypatch.setattr(protocol.documents_cache.analysis_config, "semantic_model", semantic_model)
    # files old enough to be trusted, otherwise their analysis is not cached
    suite = write_project(tmp_path, CASES[case]) / "suite.robot"

    try:
        # without a version, as a file that is not open in the editor: only such a namespace is cached
        fresh = _references_to_imports(protocol, protocol.documents.get_or_open_document(suite, "robotframework"))
        _close_project(protocol, tmp_path)

        from_data = mocker.spy(Namespace, "from_data")
        restored = _references_to_imports(protocol, protocol.documents.get_or_open_document(suite, "robotframework"))
    finally:
        _close_project(protocol, tmp_path)

    # the second namespace really comes from the cache; compared as paths, because on Windows
    # the source of a namespace has a lower-case drive letter
    assert any(Path(call.args[0].source) == suite for call in from_data.call_args_list)
    assert restored == fresh
