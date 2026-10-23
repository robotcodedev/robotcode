"""Tests for the references to imports of a namespace restored from the namespace disk cache.

A suite is opened, closed and opened again. The first time its namespace is
analyzed fresh and stored in the cache; the second time it is restored from
there. Both namespaces must have the same entries in `namespace_references`,
also when the suite imports something that is already loaded implicitly or
through a resource file. A restored semantic model must refer to the keywords
and imports of the restored namespace, also after the editor opens the file.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from pytest_mock import MockerFixture

from robotcode.core.lsp.types import Position, Range, TextDocumentItem
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.diagnostics.semantic_analyzer.nodes import ImportStatement, KeywordCallStatement
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


MODEL_SUITE = """\
*** Settings ***
Library      Collections
Variables    vars.py    first

*** Test Cases ***
First
    Log    hello
    Collections.Append To List    ${LIST}    1
"""

VARS_WITH_ARGUMENTS = """\
def get_variables(name):
    return {"NAME": name}
"""

# (line, character) of `Collections` in the import, of `Log` and of `Append To List`
_MODEL_TARGET_POSITIONS = [(1, 14), (6, 5), (7, 20)]


def _documentation_targets(protocol: RobotLanguageServerProtocol, document: TextDocument) -> List[Any]:
    documentation = protocol.robot_code_action_documentation
    return [
        documentation.target_at(document, Range(Position(line, character), Position(line, character)))
        for line, character in _MODEL_TARGET_POSITIONS
    ]


def test_restored_semantic_model_refers_to_the_restored_keywords_and_imports(
    protocol: RobotLanguageServerProtocol,
    tmp_path: Path,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(protocol.documents_cache.analysis_config, "semantic_model", True)
    suite = write_project(tmp_path, {"suite.robot": MODEL_SUITE, "vars.py": VARS_WITH_ARGUMENTS}) / "suite.robot"

    try:
        fresh = _documentation_targets(protocol, protocol.documents.get_or_open_document(suite, "robotframework"))
        _close_project(protocol, tmp_path)

        from_data = mocker.spy(Namespace, "from_data")
        document = protocol.documents.get_or_open_document(suite, "robotframework")
        namespace = protocol.documents_cache.get_namespace(document)
        # the editor opens the file with unchanged text, which keeps the restored namespace
        protocol.documents._text_document_did_open(
            TextDocumentItem(str(document.uri), "robotframework", 1, document.text())
        )
        assert protocol.documents_cache.get_namespace(document) is namespace
        restored = _documentation_targets(protocol, document)
    finally:
        _close_project(protocol, tmp_path)

    assert any(Path(call.args[0].source) == suite for call in from_data.call_args_list)
    assert restored == fresh
    assert all(target is not None for target in restored)

    model = namespace.semantic_model
    assert model is not None
    collections_import, variables_import, log, append = (model.statement_at(line) for line in (2, 3, 7, 8))
    assert isinstance(collections_import, ImportStatement)
    assert isinstance(variables_import, ImportStatement)
    assert isinstance(log, KeywordCallStatement)
    assert isinstance(append, KeywordCallStatement)
    builtin = namespace.libraries["BuiltIn"]
    collections = namespace.libraries["Collections"]
    variables = next(iter(namespace.variables_imports.values()))
    # the objects of the restored namespace, not copies
    assert any(keyword is log.keyword_doc for keyword in builtin.library_doc.keywords)
    assert log.keyword_doc is not None
    assert log.keyword_doc.parent is builtin.library_doc
    assert append.lib_entry is collections
    assert any(keyword is append.keyword_doc for keyword in collections.library_doc.keywords)
    assert collections_import.lib_entry is collections
    assert variables_import.lib_entry is variables
    # only Robot Framework < 7.0 gives a variables file an init
    assert variables_import.init_keyword_doc is next(iter(variables.library_doc.inits), None)
