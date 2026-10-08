"""Tests for the files a namespace in the namespace disk cache depends on.

Each test runs two language-server sessions on the same workspace, one after
the other, as after a restart of the editor. The first session stores the
namespace of the closed suite in the cache. The second one restores it from
there only when none of the files the namespace depends on has changed, also
when two of them are imported with the same name from different folders.
"""

import os
import threading
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Set

from pytest_mock import MockerFixture

from robotcode.core.lsp.types import (
    ClientCapabilities,
    InitializedParams,
    InitializeParamsClientInfoType,
    WorkspaceFolder,
)
from robotcode.core.utils.dataclasses import as_dict
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import AnalysisConfig, RobotCodeConfig
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer
from robotcode.robot.diagnostics.errors import Error
from robotcode.robot.diagnostics.namespace import Namespace
from tests.robotcode.language_server.robotframework.tools import write_project


def _start(root: Path) -> RobotLanguageServerProtocol:
    """A language server for the workspace `root`, after its workspace analysis."""
    protocol = RobotLanguageServerProtocol(RobotLanguageServer())
    protocol._initialize(
        ClientCapabilities(),
        root_path=str(root),
        root_uri=root.as_uri(),
        workspace_folders=[WorkspaceFolder(name="workspace", uri=root.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
        initialization_options={},
    )
    protocol.workspace.settings = {
        RobotCodeConfig.__config_section__: as_dict(
            RobotCodeConfig(analysis=AnalysisConfig(diagnostic_mode=DiagnosticsMode.OFF)), encode=False
        )
    }

    analyzed = threading.Event()

    def on_workspace_analyzed(sender: Any) -> None:
        analyzed.set()

    # before the start, the analysis of a small workspace can end before the handler is added;
    # the event keeps only a weak reference, so the handler stays referenced until the wait is over
    protocol.diagnostics.on_workspace_diagnostics_end.add(on_workspace_analyzed)
    protocol._initialized(InitializedParams())
    assert analyzed.wait(120), "the workspace analysis did not end"
    return protocol


class _Session(NamedTuple):
    restored: bool  # the suite's namespace came from the cache
    not_found: List[str]  # the variables and keywords the suite reports as not found
    files: Set[Path]  # the library and variable files the suite's namespace depends on, by their path


def _session(project: Path, mocker: MockerFixture) -> _Session:
    """Run a session and return what it gives for the suite."""
    suite = project / "suite.robot"
    from_data = mocker.spy(Namespace, "from_data")
    protocol = _start(project)
    try:
        namespace = protocol.documents_cache.get_namespace(protocol.documents.get_or_open_document(suite))
        not_found = sorted(
            d.message for d in namespace.diagnostics if d.code in (Error.VARIABLE_NOT_FOUND, Error.KEYWORD_NOT_FOUND)
        )
        # a dependency imported by path is recorded under its path, a module import under its module name
        files = {
            Path(key[4:]).resolve()
            for key in namespace.dependency_metas or {}
            if key.startswith(("lib:", "var:")) and os.path.isabs(key[4:])
        }
    finally:
        protocol._shutdown()
        mocker.stop(from_data)
    return _Session(any(call.args[0].source == str(suite) for call in from_data.call_args_list), not_found, files)


def _variables_project(settings: str) -> Dict[str, str]:
    return {
        "suite.robot": f"*** Settings ***\n{settings}\n"
        "*** Test Cases ***\nFirst\n    Log    ${TOP}\n    Log    ${SUB}\n",
        "vars.py": "TOP = 1\n",
        "sub/r.resource": "*** Settings ***\nVariables    vars.py\n",
        "sub/vars.py": "SUB = 1\n",
    }


def test_a_changed_variable_file_with_the_name_of_another_one_is_noticed(tmp_path: Path, mocker: MockerFixture) -> None:
    write_project(tmp_path, _variables_project("Variables    vars.py\nResource     sub/r.resource\n"))
    first = _session(tmp_path, mocker)
    assert (first.restored, first.not_found) == (False, [])
    # both files named vars.py are dependencies of their own
    assert {(tmp_path / "vars.py").resolve(), (tmp_path / "sub" / "vars.py").resolve()} <= first.files

    write_project(tmp_path, {"vars.py": "OTHER = 1\n"})

    second = _session(tmp_path, mocker)
    assert not second.restored
    assert [m for m in second.not_found if "${TOP}" in m]


def test_a_changed_library_file_with_the_name_of_another_one_is_noticed(tmp_path: Path, mocker: MockerFixture) -> None:
    write_project(
        tmp_path,
        {
            "suite.robot": "*** Settings ***\nLibrary      helper.py\nResource     sub/r.resource\n\n"
            "*** Test Cases ***\nFirst\n    Top Kw\n",
            "helper.py": "def top_kw():\n    pass\n",
            "sub/r.resource": "*** Settings ***\nLibrary      helper.py\n",
            "sub/helper.py": "def sub_kw():\n    pass\n",
        },
    )
    first = _session(tmp_path, mocker)
    assert (first.restored, first.not_found) == (False, [])
    # both files named helper.py are dependencies of their own
    assert {(tmp_path / "helper.py").resolve(), (tmp_path / "sub" / "helper.py").resolve()} <= first.files

    write_project(tmp_path, {"helper.py": "def other_kw():\n    pass\n"})

    second = _session(tmp_path, mocker)
    assert not second.restored
    assert [m for m in second.not_found if "'Top Kw'" in m]


def test_an_unchanged_namespace_is_restored(tmp_path: Path, mocker: MockerFixture) -> None:
    # the resource file first: the check used to look for its vars.py in the suite's folder
    write_project(tmp_path, _variables_project("Resource     sub/r.resource\nVariables    vars.py\n"))
    first = _session(tmp_path, mocker)
    assert (first.restored, first.not_found) == (False, [])

    second = _session(tmp_path, mocker)
    assert (second.restored, second.not_found) == (True, [])
