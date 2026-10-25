"""The completion of a target in the target field of the Documentation Viewer."""

from pathlib import Path
from typing import Iterator, List, Tuple

import pytest

from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from tests.robotcode.language_server.robotframework.tools import language_server, write_project

LIBRARY = """\
def open_shop():
    pass
"""

RESOURCE = """\
*** Keywords ***
Open The Shop
    No Operation
"""

SUITE = """\
*** Test Cases ***
First
    No Operation
"""


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_project(
        tmp_path_factory.mktemp("viewer_targets"),
        {
            "libraries/ShopLibrary.py": LIBRARY,
            "resources/shop.resource": RESOURCE,
            "tests/login.robot": SUITE,
            # a name with a character outside the Basic Multilingual Plane, two UTF-16 code units long
            "📁docs/a.resource": RESOURCE,
        },
    )


@pytest.fixture(scope="module")
def server(project: Path) -> Iterator[RobotLanguageServerProtocol]:
    with language_server(project, python_path=["libraries"]) as protocol:
        yield protocol


def complete(server: RobotLanguageServerProtocol, project: Path, text: str) -> List[Tuple[str, str, int]]:
    return [
        (completion.label, completion.kind, completion.start)
        for completion in server.robot_documentation_viewer._complete_target(project.as_uri(), text)
    ]


def test_standard_library(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert ("Collections", "MODULE_INTERNAL", 0) in complete(server, project, "Coll")


def test_typed_part_in_another_case(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert ("Collections", "MODULE_INTERNAL", 0) in complete(server, project, "coll")


def test_only_names_that_start_with_the_typed_part(server: RobotLanguageServerProtocol, project: Path) -> None:
    labels = [label for label, _, _ in complete(server, project, "Coll")]

    assert labels
    assert all(label.lower().startswith("coll") for label in labels)


def test_directory_of_the_folder_once(server: RobotLanguageServerProtocol, project: Path) -> None:
    # Library and resource completion both list the directory; it is offered once.
    completions = server.robot_documentation_viewer._complete_target(project.as_uri(), "res")

    assert [(c.label, c.detail, c.start) for c in completions if c.label == "resources" and c.kind == "FOLDER"] == [
        ("resources", "Directory", 0)
    ]


def test_resource_in_a_directory_of_the_folder(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert ("shop.resource", "RESOURCE", len("resources/")) in complete(server, project, "resources/")
    assert ("shop.resource", "RESOURCE", len("resources/")) in complete(server, project, "resources/sh")


def test_suite_file(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert ("login.robot", "RESOURCE", len("tests/")) in complete(server, project, "tests/")


def test_library_file(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert ("ShopLibrary.py", "FILE", len("libraries/")) in complete(server, project, "libraries/")


def test_module_on_the_python_path(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert ("ShopLibrary", "MODULE", 0) in complete(server, project, "Shop")


def test_absolute_path(server: RobotLanguageServerProtocol, project: Path) -> None:
    text = f"{project.as_posix()}/resources/"

    assert ("shop.resource", "RESOURCE", len(text)) in complete(server, project, text)


def test_no_completion_of_import_arguments(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert complete(server, project, "Collections::") == []


def test_sorted_by_label(server: RobotLanguageServerProtocol, project: Path) -> None:
    labels = [label for label, _, _ in complete(server, project, "")]

    assert labels == sorted(labels, key=str.lower)


def test_names_in_the_typed_case_first(server: RobotLanguageServerProtocol, project: Path) -> None:
    # Python's `collections` from the standard library is on the Python path, as a module and as a directory.
    assert complete(server, project, "Coll")[:3] == [
        ("Collections", "MODULE_INTERNAL", 0),
        ("collections", "MODULE", 0),
        ("collections", "FOLDER", 0),
    ]


def test_names_in_another_case_after_all_in_the_typed_case(server: RobotLanguageServerProtocol, project: Path) -> None:
    completions = complete(server, project, "xml")
    standard_library = completions.index(("XML", "MODULE_INTERNAL", 0))

    assert completions[:2] == [("xml", "MODULE", 0), ("xml", "FOLDER", 0)]
    assert all(label.startswith("xml") for label, _, _ in completions[:standard_library])
    assert all(not label.startswith("xml") for label, _, _ in completions[standard_library:])


def test_builtin(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert ("BuiltIn", "MODULE_INTERNAL", 0) in complete(server, project, "Bui")


def test_editor_import_completion_still_leaves_out_builtin(server: RobotLanguageServerProtocol, project: Path) -> None:
    imports_manager = server.documents_cache.get_imports_manager_for_uri(Uri(project.as_uri()))

    assert all(result.label != "BuiltIn" for result in imports_manager.complete_library_import(None, str(project)))


@pytest.mark.parametrize("text", [".", ".."], ids=["dot", "two-dots"])
def test_no_completion_of_dots_only(server: RobotLanguageServerProtocol, project: Path, text: str) -> None:
    assert complete(server, project, text) == []


def test_start_in_utf16_code_units(server: RobotLanguageServerProtocol, project: Path) -> None:
    assert ("a.resource", "RESOURCE", len("📁docs/".encode("utf-16-le")) // 2) in complete(server, project, "📁docs/")
