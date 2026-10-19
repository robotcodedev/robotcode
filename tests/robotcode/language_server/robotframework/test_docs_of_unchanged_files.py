"""The doc of a closed file that did not change on disk is reused when the file is analyzed again.

A file's doc holds only what the file itself defines. What depends on the files
it imports is in its namespace, which is rebuilt when an imported file changes.
Each test runs its own language server session on a project in `tmp_path`,
whose files are old enough that their states on disk are trusted.
"""

from pathlib import Path

from robotcode.core.lsp.types import (
    FileChangeType,
    Position,
    Range,
    TextDocumentContentChangeEventType1,
    TextDocumentItem,
    VersionedTextDocumentIdentifier,
)
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.diagnostics.namespace import Namespace
from tests.robotcode.language_server.robotframework.tools import (
    document_of,
    language_server,
    report_file_event,
    wait_until,
    write_project,
)

RESOURCE = "*** Keywords ***\nShared\n    No Operation\n"
ADDED_KEYWORD = "\nAdded Keyword\n    No Operation\n"
SUITE = (
    "*** Settings ***\nResource    common.resource\n\n"
    "*** Test Cases ***\nFirst\n    Added Keyword\n\n"
    "*** Keywords ***\nOwn Keyword\n    No Operation\n"
)


def _namespace(protocol: RobotLanguageServerProtocol, suite: Path) -> Namespace:
    namespace = protocol.documents_cache.get_only_initialized_namespace(document_of(protocol, suite))
    assert namespace is not None, f"{suite.name} has no analysis"
    return namespace


def _next_namespace(protocol: RobotLanguageServerProtocol, suite: Path, previous: Namespace) -> Namespace:
    wait_until(
        lambda: protocol.documents_cache.get_only_initialized_namespace(document_of(protocol, suite)) is not previous,
        f"{suite.name} was not analyzed again",
    )
    return _namespace(protocol, suite)


def test_a_change_of_an_imported_file_on_disk_keeps_the_own_doc(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"common.resource": RESOURCE, "suite.robot": SUITE})
    with language_server(project) as protocol:
        suite = project / "suite.robot"
        previous = _namespace(protocol, suite)

        (project / "common.resource").write_text(RESOURCE + ADDED_KEYWORD, encoding="utf-8")
        report_file_event(protocol, project / "common.resource", FileChangeType.CHANGED)
        namespace = _next_namespace(protocol, suite, previous)

        assert namespace.library_doc is previous.library_doc
        assert namespace.find_keyword("Added Keyword") is not None


def test_a_change_of_an_imported_file_in_the_editor_reaches_the_analysis(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"common.resource": RESOURCE, "suite.robot": SUITE})
    with language_server(project) as protocol:
        suite = project / "suite.robot"
        resource = project / "common.resource"
        previous = _namespace(protocol, suite)

        protocol.documents._text_document_did_open(TextDocumentItem(resource.as_uri(), "robotframework", 1, RESOURCE))
        end = Position(RESOURCE.count("\n"), 0)
        protocol.documents._text_document_did_change(
            VersionedTextDocumentIdentifier(uri=resource.as_uri(), version=2),
            [TextDocumentContentChangeEventType1(range=Range(end, end), text=ADDED_KEYWORD)],
        )
        namespace = _next_namespace(protocol, suite, previous)

        assert namespace.find_keyword("Added Keyword") is not None


def test_a_change_of_the_file_on_disk_gives_it_a_new_own_doc(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"common.resource": RESOURCE, "suite.robot": SUITE})
    with language_server(project) as protocol:
        suite = project / "suite.robot"
        previous = _namespace(protocol, suite)

        suite.write_text(SUITE + "\nSecond Own Keyword\n    No Operation\n", encoding="utf-8")
        report_file_event(protocol, suite, FileChangeType.CHANGED)
        namespace = _next_namespace(protocol, suite, previous)

        assert namespace.library_doc is not previous.library_doc
        assert namespace.find_keyword("Second Own Keyword") is not None
