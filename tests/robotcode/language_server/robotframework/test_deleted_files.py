"""Tests for Robot Framework files that are deleted while the language server runs.

The server removes their entries from the analysis cache, and a document that
was deleted while it was open in the editor is dropped when the editor closes
it. Each test runs its own language server session on a project in `tmp_path`.
"""

from pathlib import Path
from typing import List

from pytest_mock import MockerFixture

from robotcode.core.lsp.types import Diagnostic, FileChangeType, TextDocumentIdentifier, TextDocumentItem
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.diagnostics.data_cache import CacheSection
from tests.robotcode.language_server.robotframework.tools import (
    document_of,
    files_with_calls,
    keyword_in,
    language_server,
    report_file_event,
    wait_until,
    write_project,
)

SUITE = "*** Test Cases ***\nFirst\n    Log    {}\n"


def _cached_files(protocol: RobotLanguageServerProtocol) -> List[str]:
    """The names of the files with entries in the analysis cache, with the section of each entry."""
    folder = protocol.workspace.workspace_folders[0]
    data_cache = protocol.documents_cache.get_imports_manager_for_workspace_folder(folder).data_cache
    return sorted(
        f"{Path(entry.entry_name.split(chr(10), 1)[0]).name} ({section.value})"
        for section in (CacheSection.NAMESPACE, CacheSection.RESOURCE)
        for entry in data_cache.list_entries(section)
    )


def test_the_cache_keeps_no_entries_of_a_deleted_file(tmp_path: Path) -> None:
    project = write_project(
        tmp_path,
        {
            "common.resource": "*** Keywords ***\nShared\n    No Operation\n",
            "a.robot": "*** Settings ***\nResource    common.resource\n\n*** Test Cases ***\nFirst\n    Shared\n",
        },
    )
    with language_server(project) as protocol:
        assert {"common.resource (namespace)", "common.resource (resource)"} <= set(_cached_files(protocol))

        (project / "common.resource").unlink()
        report_file_event(protocol, project / "common.resource", FileChangeType.DELETED)

        assert [name for name in _cached_files(protocol) if name.startswith("common.resource")] == []
        assert "a.robot (namespace)" in _cached_files(protocol)


def test_a_document_deleted_while_open_is_dropped_when_the_editor_closes_it(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a"), "b.robot": SUITE.format("b")})
    with language_server(project) as protocol:
        a = document_of(protocol, project / "a.robot")
        log = keyword_in(protocol, a, "Log")
        b = project / "b.robot"
        protocol.documents._text_document_did_open(
            TextDocumentItem(b.as_uri(), "robotframework", 1, b.read_text(encoding="utf-8"))
        )
        assert files_with_calls(protocol, a, log) == ["a.robot", "b.robot"]
        assert "b.robot (namespace)" in _cached_files(protocol)
        publish = mocker.patch.object(
            protocol.diagnostics, "publish_diagnostics", wraps=protocol.diagnostics.publish_diagnostics
        )

        b.unlink()
        protocol.documents._text_document_did_close(TextDocumentIdentifier(b.as_uri()))

        assert protocol.documents.get(Uri.from_path(b).normalized()) is None
        assert files_with_calls(protocol, a, log) == ["a.robot"]
        assert [name for name in _cached_files(protocol) if name.startswith("b.robot")] == []

        def published_for_b() -> List[List[Diagnostic]]:
            return [
                call.kwargs["diagnostics"] if "diagnostics" in call.kwargs else call.args[1]
                for call in publish.call_args_list
                if (call.args[0] if call.args else call.kwargs["document"]).uri.to_path().name == "b.robot"
            ]

        # the close publishes no problems for the file, and nothing publishes any later
        wait_until(lambda: bool(published_for_b()), "no diagnostics were published for the closed file")
        assert protocol.diagnostics.workspace_analyzed_event.wait(60)
        assert all(not diagnostics for diagnostics in published_for_b()), published_for_b()
