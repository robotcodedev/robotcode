"""Tests for the references of the workspace following its files.

Each test runs its own language server session on a project in `tmp_path`, so
that what it creates, changes and deletes stays out of the other tests. Find
References, Rename, the references code lens and the unused hints all read the
references through `find_keyword_references` of the references part.
"""

import threading
from pathlib import Path
from typing import Any, List, Set

import pytest
from pytest_mock import MockerFixture

from robotcode.core.lsp.types import (
    Diagnostic,
    FileChangeType,
    Position,
    Range,
    TextDocumentContentChangeEventType1,
    TextDocumentEdit,
    TextDocumentItem,
    VersionedTextDocumentIdentifier,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import AnalysisConfig
from robotcode.robot.diagnostics.namespace import Namespace
from tests.robotcode.language_server.robotframework.tools import (
    document_of,
    files_with_calls,
    is_analyzed,
    keyword_in,
    language_server,
    report_file_event,
    stop_workspace_diagnostics,
    wait_until,
    write_project,
)

SUITE = "*** Test Cases ***\nFirst\n    Log    {}\n"
SUITE_WITH_RESOURCE = "*** Settings ***\nResource    common.resource\n\n*** Test Cases ***\nFirst\n    {}\n"
WITHOUT_NEW_KEYWORD = "*** Keywords ***\nShared\n    No Operation\n"
WITH_NEW_KEYWORD = WITHOUT_NEW_KEYWORD + "\nNew Keyword\n    No Operation\n"
SUITE_CALLING_NEW_KEYWORD = SUITE_WITH_RESOURCE.format("New Keyword")
SUITES_CALLING_NEW_KEYWORD = [f"suite{i}.robot" for i in range(1, 9)]


def test_references_stay_until_the_renewed_analysis_replaces_them(tmp_path: Path) -> None:
    project = write_project(
        tmp_path,
        {
            "common.resource": "*** Keywords ***\nShared\n    No Operation\n",
            "a.robot": SUITE_WITH_RESOURCE.format("Log    a"),
            "b.robot": SUITE_WITH_RESOURCE.format("Log    b"),
        },
    )
    with language_server(project) as protocol:
        # the suites are analyzed again only where the test asks for it
        stop_workspace_diagnostics(protocol)
        a = document_of(protocol, project / "a.robot")
        b = document_of(protocol, project / "b.robot")
        log = keyword_in(protocol, a, "Log")
        assert files_with_calls(protocol, a, log) == ["a.robot", "b.robot"]

        invalidated: Set[str] = set()

        def on_invalidated(sender: Any, namespace: Namespace) -> None:
            invalidated.add(Path(namespace.source).name)

        protocol.documents_cache.namespace_invalidated.add(on_invalidated)

        (project / "common.resource").write_text(
            "*** Keywords ***\nShared\n    No Operation\n    No Operation\n", encoding="utf-8"
        )
        report_file_event(protocol, project / "common.resource", FileChangeType.CHANGED)
        wait_until(lambda: {"a.robot", "b.robot"} <= invalidated, "the analyses of the suites stayed valid")

        assert files_with_calls(protocol, a, log) == ["a.robot", "b.robot"]

        protocol.documents_cache.get_namespace(a)
        protocol.documents_cache.get_namespace(b)
        assert files_with_calls(protocol, a, log) == ["a.robot", "b.robot"]


def test_a_document_closed_for_good_before_its_turn_is_not_analyzed(tmp_path: Path, mocker: MockerFixture) -> None:
    project = write_project(
        tmp_path,
        {
            "a.robot": "*** Test Cases ***\nFirst\n    Unknown Keyword\n",
            "b.robot": "*** Test Cases ***\nFirst\n    Unknown Keyword\n",
        },
    )
    with language_server(project, AnalysisConfig(diagnostic_mode=DiagnosticsMode.WORKSPACE)) as protocol:
        diagnostics = protocol.diagnostics
        analyse_document = diagnostics._analyse_document
        analyzed: List[TextDocument] = []
        closed: List[TextDocument] = []

        # the first analysis of the pass closes the other document for good
        def analyse(document: TextDocument) -> Any:
            if not closed:
                other = next(d for d in protocol.documents.documents if d is not document)
                protocol.documents.close_document(other, real_close=True)
                closed.append(other)
            analyzed.append(document)
            return analyse_document(document)

        mocker.patch.object(diagnostics, "_analyse_document", side_effect=analyse)
        publish = mocker.patch.object(diagnostics, "publish_diagnostics", wraps=diagnostics.publish_diagnostics)

        diagnostics.force_refresh_all()
        wait_until(
            lambda: bool(closed) and diagnostics.workspace_analyzed_event.is_set(),
            "the workspace analysis did not end",
        )

        assert closed[0] not in analyzed
        # closing it publishes no problems for it, and nothing may publish any later
        published: List[List[Diagnostic]] = [
            call.kwargs["diagnostics"] if "diagnostics" in call.kwargs else call.args[1]
            for call in publish.call_args_list
            if (call.args[0] if call.args else call.kwargs["document"]) is closed[0]
        ]
        assert all(not d for d in published), published


def test_a_deleted_suite_has_no_references(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a"), "b.robot": SUITE.format("b")})
    with language_server(project) as protocol:
        a = document_of(protocol, project / "a.robot")
        log = keyword_in(protocol, a, "Log")
        assert files_with_calls(protocol, a, log) == ["a.robot", "b.robot"]

        (project / "b.robot").unlink()
        report_file_event(protocol, project / "b.robot", FileChangeType.DELETED)

        assert files_with_calls(protocol, a, log) == ["a.robot"]


def test_renaming_a_keyword_changes_nothing_in_a_deleted_suite(tmp_path: Path) -> None:
    project = write_project(
        tmp_path,
        {
            "common.resource": "*** Keywords ***\nMy Keyword\n    No Operation\n",
            "a.robot": SUITE_WITH_RESOURCE.format("My Keyword"),
            "b.robot": SUITE_WITH_RESOURCE.format("My Keyword"),
        },
    )
    with language_server(project) as protocol:
        (project / "b.robot").unlink()
        report_file_event(protocol, project / "b.robot", FileChangeType.DELETED)

        resource = document_of(protocol, project / "common.resource")
        edit = protocol.robot_rename.collect(None, resource, Position(1, 0), "Your Keyword")

        assert edit is not None
        assert edit.document_changes is not None
        changed = {
            Uri(change.text_document.uri).to_path().name
            for change in edit.document_changes
            if isinstance(change, TextDocumentEdit)
        }
        assert changed == {"a.robot", "common.resource"}


def test_a_document_analyzed_after_it_was_closed_for_good_adds_nothing(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a"), "late.robot": SUITE.format("late")})
    with language_server(project) as protocol:
        stop_workspace_diagnostics(protocol)
        a = document_of(protocol, project / "a.robot")
        late = document_of(protocol, project / "late.robot")
        log = keyword_in(protocol, a, "Log")

        protocol.documents.close_document(late, real_close=True)
        # an analysis that ends after the close
        protocol.documents_cache.get_namespace(late)

        assert files_with_calls(protocol, a, log) == ["a.robot"]


def test_a_created_missing_resource_file_is_found_by_the_suite_that_imports_it(tmp_path: Path) -> None:
    project = write_project(
        tmp_path,
        {
            "suite.robot": "*** Settings ***\nResource    later.resource\n\n"
            "*** Test Cases ***\nFirst\n    Later Keyword\n"
        },
    )
    with language_server(project) as protocol:
        suite = document_of(protocol, project / "suite.robot")

        def imports_later_resource() -> bool:
            # reads the latest analysis without starting one
            namespace = protocol.documents_cache.get_only_initialized_namespace(suite)
            return namespace is not None and any(
                Path(entry.library_doc.source or "").name == "later.resource" for entry in namespace.resources.values()
            )

        assert not imports_later_resource()

        write_project(project, {"later.resource": "*** Keywords ***\nLater Keyword\n    No Operation\n"})
        report_file_event(protocol, project / "later.resource", FileChangeType.CREATED)
        wait_until(imports_later_resource, "the suite was not analyzed again")

        assert files_with_calls(protocol, suite, keyword_in(protocol, suite, "Later Keyword")) == ["suite.robot"]


def test_an_unrelated_created_file_keeps_the_references_of_the_other_files(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a"), "b.robot": SUITE.format("b")})
    with language_server(project) as protocol:
        a = document_of(protocol, project / "a.robot")
        log = keyword_in(protocol, a, "Log")
        assert files_with_calls(protocol, a, log) == ["a.robot", "b.robot"]

        invalidated: Set[str] = set()

        def on_invalidated(sender: Any, namespace: Namespace) -> None:
            invalidated.add(Path(namespace.source).name)

        protocol.documents_cache.namespace_invalidated.add(on_invalidated)

        write_project(project, {"helper.py": "def helper():\n    pass\n"})
        report_file_event(protocol, project / "helper.py", FileChangeType.CREATED)

        assert files_with_calls(protocol, a, log) == ["a.robot", "b.robot"]
        # analyses without a failed import stay valid
        assert invalidated == set()


def test_a_suite_created_outside_the_editoris_analyzed(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a")})
    with language_server(project) as protocol:
        a = document_of(protocol, project / "a.robot")
        log = keyword_in(protocol, a, "Log")
        assert files_with_calls(protocol, a, log) == ["a.robot"]

        write_project(project, {"new.robot": SUITE.format("new")})
        report_file_event(protocol, project / "new.robot", FileChangeType.CREATED)
        wait_until(lambda: is_analyzed(protocol, project / "new.robot"), "the created suite was not analyzed")

        assert files_with_calls(protocol, a, log) == ["a.robot", "new.robot"]


def test_a_suite_created_in_an_excluded_folder_is_not_analyzed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a")})
    with language_server(project) as protocol:
        monkeypatch.setattr(protocol.analysis_config, "exclude_patterns", ["excluded/"])

        write_project(project, {"excluded/new.robot": SUITE.format("new")})
        report_file_event(protocol, project / "excluded" / "new.robot", FileChangeType.CREATED)

        assert protocol.documents.get(Uri.from_path(project / "excluded" / "new.robot").normalized()) is None


def test_a_lookup_during_an_analysis_is_not_kept_after_it(tmp_path: Path, mocker: MockerFixture) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a")})
    with language_server(project) as protocol:
        a = document_of(protocol, project / "a.robot")
        log = keyword_in(protocol, a, "Log")
        diagnostics = protocol.diagnostics
        analyse_document = diagnostics._analyse_document
        release = threading.Event()

        # the analysis of the created suite waits until Find References ran
        def analyse(document: TextDocument) -> Any:
            if document.uri.to_path().name == "new.robot":
                release.wait(30)
            return analyse_document(document)

        mocker.patch.object(diagnostics, "_analyse_document", side_effect=analyse)

        write_project(project, {"new.robot": SUITE.format("new")})
        report_file_event(protocol, project / "new.robot", FileChangeType.CREATED)
        assert files_with_calls(protocol, a, log) == ["a.robot"]

        release.set()
        wait_until(
            lambda: files_with_calls(protocol, a, log) == ["a.robot", "new.robot"],
            "Find References kept the result it found during the analysis",
        )


def test_a_lookup_sees_an_analysis_made_after_it(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a")})
    with language_server(project) as protocol:
        # only the analysis below renews anything
        stop_workspace_diagnostics(protocol)
        a = document_of(protocol, project / "a.robot")
        log = keyword_in(protocol, a, "Log")
        write_project(project, {"later.robot": SUITE.format("later")})
        later = protocol.documents.get_or_open_document(project / "later.robot")
        assert files_with_calls(protocol, a, log) == ["a.robot"]

        protocol.documents_cache.get_namespace(later)

        assert files_with_calls(protocol, a, log) == ["a.robot", "later.robot"]


def _project_calling_new_keyword(root: Path) -> Path:
    suites = {name: SUITE_CALLING_NEW_KEYWORD for name in SUITES_CALLING_NEW_KEYWORD}
    return write_project(root, {"common.resource": WITHOUT_NEW_KEYWORD, **suites})


def _files_with_calls_of_new_keyword(protocol: Any, resource: Path) -> List[str]:
    document = document_of(protocol, resource)
    keyword = protocol.documents_cache.get_namespace(document).find_keyword("New Keyword")
    return [] if keyword is None else files_with_calls(protocol, document, keyword)


def test_every_suite_that_imports_a_resource_changed_in_the_editor_is_analyzed_again(tmp_path: Path) -> None:
    project = _project_calling_new_keyword(tmp_path)
    with language_server(project) as protocol:
        resource = project / "common.resource"
        protocol.documents._text_document_did_open(
            TextDocumentItem(resource.as_uri(), "robotframework", 1, WITHOUT_NEW_KEYWORD)
        )
        end = Position(WITHOUT_NEW_KEYWORD.count("\n"), 0)
        added = TextDocumentContentChangeEventType1(
            range=Range(end, end), text=WITH_NEW_KEYWORD[len(WITHOUT_NEW_KEYWORD) :]
        )
        protocol.documents._text_document_did_change(
            VersionedTextDocumentIdentifier(uri=resource.as_uri(), version=2), [added]
        )

        wait_until(
            lambda: _files_with_calls_of_new_keyword(protocol, resource) == SUITES_CALLING_NEW_KEYWORD,
            "not every suite was analyzed again after the change in the editor",
        )


def test_every_suite_that_imports_a_resource_changed_on_disk_is_analyzed_again(tmp_path: Path) -> None:
    project = _project_calling_new_keyword(tmp_path)
    with language_server(project) as protocol:
        resource = project / "common.resource"
        assert _files_with_calls_of_new_keyword(protocol, resource) == []

        resource.write_text(WITH_NEW_KEYWORD, encoding="utf-8")
        report_file_event(protocol, resource, FileChangeType.CHANGED)

        wait_until(
            lambda: _files_with_calls_of_new_keyword(protocol, resource) == SUITES_CALLING_NEW_KEYWORD,
            "not every suite was analyzed again after the change on disk",
        )
