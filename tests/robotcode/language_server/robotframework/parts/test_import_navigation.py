"""Tests for hover, Go to Definition and Find References on import statements.

A file can import a library, resource file or variable file that it already
imports, directly or through a resource file. Such an import is reported as
already imported, and its hover is the one of the import that imported it
first. A second import in the same file is a reference of the first one, so
Go to Definition on it leads to the first import. Find References on any
import of a target lists every import statement of that target once.
"""

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

import pytest

from robotcode.core.lsp.types import LocationLink, MarkupContent, Position, ReferenceContext
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.diagnostics.errors import Error

FILES = {
    "vars.py": "X = 1\n",
    "lib.resource": """\
*** Settings ***
Library      Collections
Variables    vars.py
""",
    "a.resource": """\
*** Keywords ***
A Keyword
    No Operation
""",
    "b.resource": """\
*** Settings ***
Resource     a.resource
""",
    # WITH NAME, because AS marks an alias only since Robot Framework 6.0
    "lib_twice.robot": """\
*** Settings ***
Library      Collections
Library      Collections    WITH NAME    Coll2

*** Test Cases ***
First
    Collections.Log List    ${{[]}}
    Coll2.Log List    ${{[]}}
""",
    "lib_same_twice.robot": """\
*** Settings ***
Library      OperatingSystem
Library      OperatingSystem

*** Test Cases ***
First
    OperatingSystem.Log File    x
""",
    "lib_and_vars_via_resource.robot": """\
*** Settings ***
Resource     lib.resource
Library      Collections
Variables    vars.py

*** Test Cases ***
First
    Log    ${X}
""",
    "vars_twice.robot": """\
*** Settings ***
Variables    vars.py
Variables    vars.py

*** Test Cases ***
First
    Log    ${X}
""",
    "resource_twice.robot": """\
*** Settings ***
Resource     a.resource
Resource     a.resource

*** Test Cases ***
First
    A Keyword
    a.A Keyword
""",
    "resource_via_resource.robot": """\
*** Settings ***
Resource     b.resource
Resource     a.resource

*** Test Cases ***
First
    A Keyword
    a.A Keyword
""",
}

_IMPORT = re.compile(r"^(Library|Resource|Variables)\s{2,}(\S+)")

# an import statement: file name, line (0-based, as in the protocol), import type, imported name
Import = Tuple[str, int, str, str]

IMPORTS: List[Import] = [
    (file, line, m[1], m[2])
    for file, text in FILES.items()
    for line, m in enumerate(_IMPORT.match(t) for t in text.splitlines())
    if m is not None
]

# the calls with a library or resource prefix, found by Find References on every import of the target
USAGES = {
    ("Library", "Collections"): {"lib_twice.robot:6"},
    ("Library", "OperatingSystem"): {"lib_same_twice.robot:6"},
    ("Resource", "a.resource"): {"resource_twice.robot:7", "resource_via_resource.robot:7"},
}

# the files that Go to Definition opens on an import, where it is not the imported file
DEFINITIONS = {
    # a second import in the same file leads to the first one
    "lib_same_twice.robot:2": ["lib_same_twice.robot"],
    "vars_twice.robot:2": ["vars_twice.robot"],
    "resource_twice.robot:2": ["resource_twice.robot"],
    # an import with an alias is a library of its own and a reference of the first import
    "lib_twice.robot:2": ["Collections.py", "lib_twice.robot"],
}

# a repeated resource import, the import that imported the resource file first,
# and the file and line that Go to Definition on the repeated import leads to
REPEATED_RESOURCE_IMPORTS = [
    (("resource_twice.robot", 2), ("resource_twice.robot", 1), ("resource_twice.robot", 1)),
    (("resource_via_resource.robot", 2), ("b.resource", 1), ("a.resource", 0)),
]


@pytest.fixture(params=[False, True], ids=["legacy", "model"])
def documents(
    request: pytest.FixtureRequest,
    protocol: RobotLanguageServerProtocol,
    open_temp_document: Callable[[Path], TextDocument],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Dict[str, TextDocument]:
    monkeypatch.setattr(protocol.documents_cache.analysis_config, "semantic_model", request.param)
    for name, text in FILES.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return {name: open_temp_document(tmp_path / name) for name in FILES if not name.endswith(".py")}


def _on_name(document: TextDocument, line: int) -> Position:
    text = document.text().splitlines()[line]
    match = _IMPORT.match(text)
    assert match is not None
    return Position(line=line, character=match.start(2) + 1)


def _hover(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> Optional[str]:
    hover = protocol.robot_hover.collect(protocol.robot_hover, document, _on_name(document, line))
    if hover is None:
        return None
    assert isinstance(hover.contents, MarkupContent)
    return hover.contents.value


def _definitions(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> List[Tuple[str, int]]:
    result = protocol.robot_goto.collect_definition(protocol.robot_goto, document, _on_name(document, line))
    return sorted(
        (Uri(d.target_uri).to_path().name, d.target_selection_range.start.line)
        if isinstance(d, LocationLink)
        else (Uri(d.uri).to_path().name, d.range.start.line)
        for d in (result if isinstance(result, list) else [result] if result else [])
    )


def _diagnostic_codes(protocol: RobotLanguageServerProtocol, document: TextDocument, line: int) -> List[str]:
    namespace = protocol.documents_cache.get_namespace(document)
    return [str(d.code) for d in namespace.diagnostics if d.range.start.line == line]


def test_hover_of_every_import_shows_its_target(
    protocol: RobotLanguageServerProtocol, documents: Dict[str, TextDocument]
) -> None:
    def heading(hover: Optional[str]) -> Optional[str]:
        return hover.splitlines()[0] if hover else None

    assert {f"{file}:{line}": heading(_hover(protocol, documents[file], line)) for file, line, _, _ in IMPORTS} == {
        f"{file}:{line}": f"### {kind} *{Path(name).stem}*" for file, line, kind, name in IMPORTS
    }


def test_definition_of_every_import(protocol: RobotLanguageServerProtocol, documents: Dict[str, TextDocument]) -> None:
    def files(file: str, line: int) -> List[str]:
        return [name for name, _ in _definitions(protocol, documents[file], line)]

    assert {f"{file}:{line}": files(file, line) for file, line, _, _ in IMPORTS} == {
        f"{file}:{line}": DEFINITIONS.get(f"{file}:{line}", [f"{name}.py" if kind == "Library" else name])
        for file, line, kind, name in IMPORTS
    }


@pytest.mark.parametrize(("repeated", "first", "definition"), REPEATED_RESOURCE_IMPORTS)
def test_a_repeated_resource_import_is_like_a_repeated_library_import(
    protocol: RobotLanguageServerProtocol,
    documents: Dict[str, TextDocument],
    repeated: Tuple[str, int],
    first: Tuple[str, int],
    definition: Tuple[str, int],
) -> None:
    repeated_document, first_document = documents[repeated[0]], documents[first[0]]

    assert _hover(protocol, repeated_document, repeated[1]) == _hover(protocol, first_document, first[1])
    assert _definitions(protocol, repeated_document, repeated[1]) == [definition]
    assert Error.RESOURCE_ALREADY_IMPORTED in _diagnostic_codes(protocol, repeated_document, repeated[1])


def _references(
    protocol: RobotLanguageServerProtocol, document: TextDocument, line: int, include_declaration: bool
) -> List[Tuple[Path, int]]:
    result = protocol.robot_references.collect(
        protocol.robot_references,
        document,
        _on_name(document, line),
        ReferenceContext(include_declaration=include_declaration),
    )
    return sorted((Uri(r.uri).to_path(), r.range.start.line) for r in result or [])


@pytest.mark.parametrize("include_declaration", [True, False], ids=["with_declaration", "without_declaration"])
def test_references_of_every_import_list_each_import_statement_once(
    protocol: RobotLanguageServerProtocol, documents: Dict[str, TextDocument], include_declaration: bool
) -> None:
    project = documents["lib_twice.robot"].uri.to_path().parent
    found = {
        f"{file}:{line}": _references(protocol, documents[file], line, include_declaration)
        for file, line, _, _ in IMPORTS
    }
    in_project = {
        key: [f"{path.name}:{line}" for path, line in locations if path.parent == project]
        for key, locations in found.items()
    }
    statements: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    for file, line, kind, name in IMPORTS:
        statements[(kind, name)].add(f"{file}:{line}")

    problems = {
        # a location found twice, also outside of the project
        "doubled": {
            key: doubled
            for key, locations in found.items()
            if (doubled := [location for location, n in Counter(locations).items() if n > 1])
        },
        # an import statement or a prefixed call of the target that is not found
        "missing": {
            f"{file}:{line}": missing
            for file, line, kind, name in IMPORTS
            if (
                missing := sorted(
                    (statements[(kind, name)] | USAGES.get((kind, name), set())) - set(in_project[f"{file}:{line}"])
                )
            )
        },
        # imports of one target with different results
        "different": {
            name: {key: in_project[key] for key in sorted(keys)}
            for (_, name), keys in statements.items()
            if len({tuple(in_project[key]) for key in keys}) > 1
        },
    }

    assert problems == {"doubled": {}, "missing": {}, "different": {}}
