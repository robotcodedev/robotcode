"""Tests for the periodic check of the workspace files.

The check finds what file events would report: created, changed and deleted
Robot Framework files, changed library and variable files, and failed imports
whose file or module exists now. Each test runs its own language server session
on a project in `tmp_path`; its client registers no file watchers, so no file
events arrive, and the tests call the check directly instead of waiting for it.
"""

from pathlib import Path
from typing import Any, List, Tuple

from pytest_mock import MockerFixture

from robotcode.core.lsp.types import FileChangeType, FileEvent
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.configuration import AnalysisConfig
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.robot.diagnostics.imports_manager import ImportsManager
from tests.robotcode.language_server.robotframework.tools import (
    document_of,
    files_with_calls,
    is_analyzed,
    keyword_in,
    language_server,
    start_language_server,
    wait_until,
    write_project,
)

SUITE = "*** Test Cases ***\nFirst\n    Log    {}\n"


def _check(protocol: RobotLanguageServerProtocol) -> List[Tuple[str, FileChangeType]]:
    """Run the check of the workspace folder, and return the file name and type of each file event it delivers."""
    delivered: List[FileEvent] = []

    def record(sender: Any, changes: List[FileEvent]) -> None:
        delivered.extend(changes)

    protocol.workspace.did_change_watched_files.add(record)
    try:
        protocol.robot_workspace.check_workspace_folder(protocol.workspace.workspace_folders[0])
    finally:
        protocol.workspace.did_change_watched_files.remove(record)
    return sorted((Uri(event.uri).to_path().name, event.type) for event in delivered)


def _failed_imports(protocol: RobotLanguageServerProtocol, path: Path) -> int:
    """The number of failed imports of the latest analysis of `path`, without starting one."""
    namespace = protocol.documents_cache.get_only_initialized_namespace(document_of(protocol, path))
    assert namespace is not None
    return len(namespace.failed_imports)


def test_the_interval_is_read_per_workspace_folder(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a")})
    with language_server(project) as protocol:
        folder = protocol.workspace.workspace_folders[0]
        assert protocol.workspace.get_configuration(AnalysisConfig, folder.uri).file_check_interval == 5

        protocol.workspace._workspace_did_change_configuration({"robotcode": {"analysis": {"fileCheckInterval": 2}}})

        assert protocol.workspace.get_configuration(AnalysisConfig, folder.uri).file_check_interval == 2


def test_deleted_changed_and_created_suites_are_handled_like_file_events(tmp_path: Path) -> None:
    project = write_project(
        tmp_path,
        {
            "kept.robot": SUITE.format("kept"),
            "changed.robot": SUITE.format("changed"),
            "deleted.robot": SUITE.format("deleted"),
        },
    )
    with language_server(project) as protocol:
        kept = document_of(protocol, project / "kept.robot")
        log = keyword_in(protocol, kept, "Log")
        assert files_with_calls(protocol, kept, log) == ["changed.robot", "deleted.robot", "kept.robot"]
        changed = document_of(protocol, project / "changed.robot")
        analysis_before = protocol.documents_cache.get_only_initialized_namespace(changed)

        (project / "deleted.robot").unlink()
        write_project(
            project,
            {
                "changed.robot": "*** Test Cases ***\nFirst\n    No Operation\n",
                "created.robot": SUITE.format("created"),
            },
        )

        assert _check(protocol) == [
            ("changed.robot", FileChangeType.CHANGED),
            ("created.robot", FileChangeType.CREATED),
            ("deleted.robot", FileChangeType.DELETED),
        ]
        wait_until(
            lambda: (
                is_analyzed(protocol, project / "created.robot")
                and protocol.documents_cache.get_only_initialized_namespace(changed) is not analysis_before
            ),
            "the changed and the created suite were not analyzed",
        )
        assert files_with_calls(protocol, kept, log) == ["created.robot", "kept.robot"]

        # the files are known as they are now
        assert _check(protocol) == []


def test_a_changed_library_file_gets_the_suite_that_imports_it_analyzed_again(tmp_path: Path) -> None:
    project = write_project(
        tmp_path,
        {
            "mylib.py": "def my_keyword():\n    pass\n",
            "suite.robot": "*** Settings ***\nLibrary    mylib.py\n\n*** Test Cases ***\nFirst\n    Other Keyword\n",
        },
    )
    with language_server(project) as protocol:
        suite = document_of(protocol, project / "suite.robot")

        def reports_other_keyword_missing() -> bool:
            namespace = protocol.documents_cache.get_only_initialized_namespace(suite)
            return namespace is not None and any("'Other Keyword'" in d.message for d in namespace.diagnostics)

        assert reports_other_keyword_missing()

        write_project(project, {"mylib.py": "def my_keyword():\n    pass\n\n\ndef other_keyword():\n    pass\n"})

        assert _check(protocol) == [("mylib.py", FileChangeType.CHANGED)]
        wait_until(lambda: not reports_other_keyword_missing(), "the suite was not analyzed again")


def test_a_library_module_created_later_resolves_the_failed_import(tmp_path: Path) -> None:
    project = write_project(
        tmp_path,
        {
            "libs/README.txt": "",
            "suite.robot": "*** Settings ***\nLibrary    later_lib\n\n*** Test Cases ***\nFirst\n    Later Keyword\n",
        },
    )
    with language_server(project, python_path=["libs"]) as protocol:
        assert _failed_imports(protocol, project / "suite.robot") == 1

        write_project(project, {"libs/later_lib.py": "def later_keyword():\n    pass\n"})

        assert _check(protocol) == [("later_lib.py", FileChangeType.CREATED)]
        wait_until(lambda: _failed_imports(protocol, project / "suite.robot") == 0, "the import still fails")


def test_a_variable_file_created_later_resolves_the_failed_import(tmp_path: Path) -> None:
    project = write_project(
        tmp_path,
        {"suite.robot": "*** Settings ***\nVariables    vars.py\n\n*** Test Cases ***\nFirst\n    Log    ${X}\n"},
    )
    with language_server(project) as protocol:
        assert _failed_imports(protocol, project / "suite.robot") == 1

        write_project(project, {"vars.py": "X = 1\n"})

        assert _check(protocol) == [("vars.py", FileChangeType.CREATED)]
        wait_until(lambda: _failed_imports(protocol, project / "suite.robot") == 0, "the import still fails")


def test_a_check_of_an_unchanged_workspace_loads_no_library(tmp_path: Path, mocker: MockerFixture) -> None:
    project = write_project(
        tmp_path,
        {
            "broken_lib.py": "raise ImportError('a package it needs is missing')\n",
            "suite.robot": "*** Settings ***\nLibrary    broken_lib.py\n\n"
            "*** Test Cases ***\nFirst\n    Log    hello\n",
        },
    )
    with language_server(project) as protocol:
        # the library is found, only loading it fails
        assert _failed_imports(protocol, project / "suite.robot") == 1
        load = mocker.spy(ImportsManager, "_run_in_subprocess")

        assert _check(protocol) == []
        assert load.call_count == 0


def test_a_changed_interval_reschedules_the_check(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a")})
    with language_server(project) as protocol:
        key = str(protocol.workspace.workspace_folders[0].uri)
        timers = protocol.robot_workspace._file_check_timers

        def interval() -> float:
            timer = timers.get(key)
            return timer.interval if timer is not None else 0

        wait_until(lambda: interval() == 5 * 60, "the check was not scheduled every 5 minutes")

        protocol.workspace._workspace_did_change_configuration({"robotcode": {"analysis": {"fileCheckInterval": 2}}})

        wait_until(lambda: interval() == 2 * 60, "the check was not rescheduled")


def test_shutdown_stops_the_check(tmp_path: Path) -> None:
    project = write_project(tmp_path, {"a.robot": SUITE.format("a")})
    protocol = start_language_server(project)
    timers = protocol.robot_workspace._file_check_timers
    wait_until(lambda: bool(timers), "the check was not scheduled")
    scheduled = list(timers.values())

    protocol._shutdown()

    assert not timers
    wait_until(lambda: not any(timer.is_alive() for timer in scheduled), "a check is still scheduled")
