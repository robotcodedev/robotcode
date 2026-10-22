from pathlib import Path
from typing import List

import pytest
import yaml

from robotcode.core.lsp.types import Location, Position, ReferenceContext
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from tests.robotcode.language_server.robotframework.tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)

from .pytest_regtestex import RegTestFixtureEx


@pytest.mark.parametrize(
    ("test_document", "data"),
    list(generate_tests_from_source_document(Path(Path(__file__).parent, "data/tests/references.robot"))),
    indirect=["test_document"],
    ids=generate_test_id,
    scope="module",
)
@pytest.mark.usefixtures("protocol")
def test(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:
    def split(location: Location) -> Location:
        return Location("/".join(location.uri.split("/")[-2:]), location.range)

    result = protocol.robot_references.collect(
        protocol.robot_references,
        test_document,
        Position(line=data.line, character=data.character),
        ReferenceContext(include_declaration=True),
    )
    regtest.write(
        yaml.dump(
            {
                "data": data,
                "result": (
                    sorted(
                        (split(v) for v in result),
                        key=lambda v: (v.uri, v.range.start, v.range.end),
                    )
                    if result
                    else result
                ),
            }
        )
    )


REFERENCES_ROBOT = Path(Path(__file__).parent, "data/tests/references.robot")
GOTO_ROBOT = Path(Path(__file__).parent, "data/tests/goto.robot")
FIRSTRESOURCE_RESOURCE = Path(Path(__file__).parent, "data/resources/firstresource.resource")


# the position of `word` in the first line of the document that starts with `line_start`
def _position(document: TextDocument, line_start: str, word: str) -> Position:
    for line, text in enumerate(document.text().splitlines()):
        if text.startswith(line_start):
            return Position(line=line, character=text.index(word))
    raise AssertionError(f"no line starts with {line_start!r}")


# the locations in the order the language server returns them
def _collect(
    protocol: RobotLanguageServerProtocol,
    document: TextDocument,
    position: Position,
    include_declaration: bool = True,
) -> List[Location]:
    result = protocol.robot_references.collect(
        protocol.robot_references,
        document,
        position,
        ReferenceContext(include_declaration=include_declaration),
    )
    return result or []


def _references(
    protocol: RobotLanguageServerProtocol,
    document: TextDocument,
    position: Position,
    include_declaration: bool = True,
) -> List[Location]:
    return sorted(
        _collect(protocol, document, position, include_declaration),
        key=lambda v: (v.uri, v.range.start.line, v.range.start.character, v.range.end.line, v.range.end.character),
    )


def _is_in(location: Location, path: Path) -> bool:
    return Uri(location.uri).to_path().resolve() == path.resolve()


def _text(location: Location) -> str:
    line = Uri(location.uri).to_path().read_text(encoding="utf-8").splitlines()[location.range.start.line]
    return line[location.range.start.character : location.range.end.character]


@pytest.mark.usefixtures("protocol")
def test_prefix_of_a_library_has_the_references_of_its_import(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(GOTO_ROBOT, "robotframework")

    on_prefix = _references(protocol, document, _position(document, "    Collections.Log Dictionary", "Collections"))
    on_import = _references(protocol, document, _position(document, "Library", "Collections"))

    assert on_prefix
    assert on_prefix == on_import


@pytest.mark.usefixtures("protocol")
def test_prefix_of_a_library_without_an_import(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(REFERENCES_ROBOT, "robotframework")
    calls = {
        line
        for line, text in enumerate(document.text().splitlines())
        if "BuiltIn." in text and not text.lstrip().startswith("#")
    }

    result = _references(protocol, document, _position(document, "Suite Setup", "BuiltIn"))

    assert result
    assert all(_text(location).lower() == "builtin" for location in result)
    assert calls <= {location.range.start.line for location in result if _is_in(location, REFERENCES_ROBOT)}


@pytest.mark.usefixtures("protocol")
def test_prefix_of_a_resource_has_the_references_of_its_import(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(REFERENCES_ROBOT, "robotframework")

    on_prefix = _references(
        protocol, document, _position(document, "    firstresource.a keyword with args", "firstresource")
    )
    on_import = _references(protocol, document, _position(document, "Resource", "firstresource"))

    assert on_prefix
    assert on_prefix == on_import


@pytest.mark.usefixtures("protocol")
def test_prefix_of_an_alias_has_the_references_of_the_alias(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(REFERENCES_ROBOT, "robotframework")

    on_prefix = _references(protocol, document, _position(document, "    ${result}    lib_hello", "lib_hello"))
    on_alias = _references(
        protocol, document, _position(document, "Library         alibrary    a_param=from hello", "lib_hello")
    )

    assert on_prefix
    assert on_prefix == on_alias


@pytest.mark.usefixtures("protocol")
def test_keyword_after_a_prefix_keeps_its_references(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(REFERENCES_ROBOT, "robotframework")
    test_setup = _position(document, "Test Setup", "Log To Console")

    result = _references(
        protocol, document, _position(document, "Suite Setup", "Log To Console"), include_declaration=False
    )

    assert any(_is_in(location, REFERENCES_ROBOT) and location.range.start == test_setup for location in result)
    assert not any(_text(location).lower() == "builtin" for location in result)


@pytest.mark.usefixtures("protocol")
def test_declaration_of_a_library_keyword_comes_last(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(REFERENCES_ROBOT, "robotframework")

    *usages, declaration = _collect(protocol, document, _position(document, "    Log    Hi", "Log"))

    assert Uri(declaration.uri).to_path().name == "BuiltIn.py"
    assert usages
    assert all(_text(location).lower() == "log" and location.uri != declaration.uri for location in usages)


@pytest.mark.usefixtures("protocol")
def test_declaration_of_a_variable_from_a_variables_file_comes_last(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(GOTO_ROBOT, "robotframework")

    *usages, declaration = _collect(
        protocol, document, _position(document, "    Log    ${A_VAR_FROM_LIB}", "A_VAR_FROM_LIB")
    )

    assert Uri(declaration.uri).to_path().name == "myvariables.py"
    assert usages
    assert all(_text(location).lower() == "a_var_from_lib" and location.uri != declaration.uri for location in usages)


@pytest.mark.usefixtures("protocol")
def test_declaration_of_a_resource_keyword_comes_last(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(REFERENCES_ROBOT, "robotframework")
    resource = protocol.documents.get_or_open_document(FIRSTRESOURCE_RESOURCE, "robotframework")

    *usages, declaration = _collect(
        protocol, document, _position(document, "    firstresource.a keyword with args", "a keyword with args")
    )

    assert _is_in(declaration, FIRSTRESOURCE_RESOURCE)
    assert declaration.range.start == _position(resource, "a keyword with args", "a keyword with args")
    assert usages
    assert all(_text(location).lower() == "a keyword with args" and location != declaration for location in usages)


@pytest.mark.usefixtures("protocol")
def test_without_the_declaration_there_are_only_usages(protocol: RobotLanguageServerProtocol) -> None:
    document = protocol.documents.get_or_open_document(REFERENCES_ROBOT, "robotframework")

    result = _collect(protocol, document, _position(document, "    Log    Hi", "Log"), include_declaration=False)

    assert result
    assert not any(Uri(location.uri).to_path().name == "BuiltIn.py" for location in result)
