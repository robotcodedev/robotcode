"""Private keywords in diagnostics and keyword completion.

Every scenario of the `private-keywords` spec runs on both analysis paths:
the legacy path (flag off) and the SemanticModel (flag on).
"""

import itertools
import threading
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import pytest

from robotcode.core.lsp.types import (
    ClientCapabilities,
    CompletionContext,
    CompletionItem,
    CompletionTriggerKind,
    InitializedParams,
    InitializeParamsClientInfoType,
    Position,
    WorkspaceFolder,
)
from robotcode.core.utils.dataclasses import as_dict, from_dict
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import AnalysisConfig, CompletionConfig, RobotCodeConfig
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer
from robotcode.robot.utils import RF_VERSION

needs_private = pytest.mark.skipif(RF_VERSION < (6, 0), reason="private keywords need Robot Framework 6.0")

_file_counter = itertools.count()

HELPERS = """\
*** Keywords ***
Public Helper
    Private Helper

Private Helper
    [Tags]    robot:private
    No Operation

Doc Private Helper
    [Documentation]    Private through its documentation.
    ...
    ...    Tags: robot:private
    No Operation
"""

PRIV_LIB = """\
from robot.api.deco import keyword


@keyword(tags=["robot:private"])
def lib_private():
    pass


def lib_public():
    pass
"""

SUITE_HEADER = """\
*** Settings ***
Resource    helpers.resource
Library    PrivLib.py

"""

OWN_KEYWORDS = """\

*** Keywords ***
Own User
    Own Helper

Own Helper
    [Tags]    robot:private
    No Operation
"""


@pytest.fixture(scope="module", params=[False, True], ids=["legacy", "model"])
def protocol(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    root = tmp_path_factory.mktemp("private_keywords")
    # outside the workspace, so the workspace scan at startup never reads a file while it is written
    files = tmp_path_factory.mktemp("private_keywords_files")
    Path(files, "helpers.resource").write_text(HELPERS, encoding="utf-8")
    Path(files, "PrivLib.py").write_text(PRIV_LIB, encoding="utf-8")

    protocol = RobotLanguageServerProtocol(RobotLanguageServer())
    protocol._initialize(
        ClientCapabilities(),
        root_path=str(root),
        root_uri=root.as_uri(),
        workspace_folders=[WorkspaceFolder(name="test workspace", uri=root.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
    )
    settings: dict[str, Any] = {
        RobotCodeConfig.__config_section__: as_dict(
            RobotCodeConfig(analysis=AnalysisConfig(diagnostic_mode=DiagnosticsMode.OFF)), encode=False
        )
    }
    if request.param:
        settings[RobotCodeConfig.__config_section__]["experimental"] = {"semantic_model": True}
    protocol.workspace.settings = settings

    diagnostics_end = threading.Event()

    def on_diagnostics_end(sender: Any) -> None:
        diagnostics_end.set()

    protocol.diagnostics.on_workspace_diagnostics_end.add(on_diagnostics_end)
    protocol._initialized(InitializedParams())
    diagnostics_end.wait(120)
    protocol.diagnostics.workspace_diagnostics_started_event.wait(300)
    protocol.diagnostics.in_get_workspace_diagnostics_event.wait(300)
    try:
        yield protocol, files, request.param
    finally:
        protocol._shutdown()


def _open(protocol: Any, text: str, suffix: str = ".robot") -> Tuple[Any, Any]:
    lsp, files, semantic_model = protocol
    path = Path(files, f"suite_{next(_file_counter)}{suffix}")
    path.write_text(text, encoding="utf-8")
    document = lsp.documents.get_or_open_document(path, "robotframework")
    namespace = lsp.documents_cache.get_namespace(document)
    assert (namespace.semantic_model is not None) == semantic_model
    return document, namespace


def _private_diagnostics(protocol: Any, text: str) -> List[Tuple[int, str]]:
    _, namespace = _open(protocol, text)
    return [(d.range.start.line, d.message) for d in namespace.diagnostics if d.code == "PrivateKeyword"]


# --- Calls of private resource keywords from other files are reported ---


@needs_private
def test_call_from_an_importing_suite(protocol: Any) -> None:
    text = SUITE_HEADER + "*** Test Cases ***\nT\n    Private Helper\n    Public Helper\n"

    assert _private_diagnostics(protocol, text) == [
        (6, "Keyword 'helpers.Private Helper' is private and should only be called by keywords in the same file.")
    ]


@needs_private
def test_call_of_a_keyword_that_is_private_through_its_documentation(protocol: Any) -> None:
    text = SUITE_HEADER + "*** Test Cases ***\nT\n    Doc Private Helper\n"

    assert _private_diagnostics(protocol, text) == [
        (6, "Keyword 'helpers.Doc Private Helper' is private and should only be called by keywords in the same file.")
    ]


def test_call_from_a_test_case_of_the_suite_file_that_defines_the_keyword(protocol: Any) -> None:
    text = SUITE_HEADER + "*** Test Cases ***\nT\n    Own Helper\n" + OWN_KEYWORDS

    assert _private_diagnostics(protocol, text) == []


# --- Calls of private library keywords are reported ---


@needs_private
def test_call_of_a_private_library_keyword(protocol: Any) -> None:
    text = SUITE_HEADER + "*** Test Cases ***\nT\n    Lib Private\n    PrivLib.Lib Private\n"

    message = "Keyword 'PrivLib.Lib Private' is private and should not be called from Robot Framework files."
    assert _private_diagnostics(protocol, text) == [(6, message), (7, message)]


def test_call_of_a_public_library_keyword(protocol: Any) -> None:
    text = SUITE_HEADER + "*** Test Cases ***\nT\n    Lib Public\n"

    assert _private_diagnostics(protocol, text) == []


@pytest.mark.skipif(RF_VERSION >= (6, 0), reason="Robot Framework 6.0 introduced private keywords")
def test_nothing_is_reported_before_robot_framework_60(protocol: Any) -> None:
    text = SUITE_HEADER + "*** Test Cases ***\nT\n    Private Helper\n    Lib Private\n"

    assert _private_diagnostics(protocol, text) == []


# --- Completion ---

# completion is requested on the empty row of the test case `T`, at row 6, and on row 7
TEST_WITH_EMPTY_ROW = "*** Test Cases ***\nT\n    \n    No Operation\n"


def _completion(
    protocol: Any, text: str, line: int, character: int, suffix: str = ".robot"
) -> Dict[str, CompletionItem]:
    lsp = protocol[0]
    document, _ = _open(protocol, text, suffix)
    result = lsp.robot_completion.collect(
        lsp.robot_completion,
        document,
        Position(line=line, character=character),
        CompletionContext(trigger_kind=CompletionTriggerKind.INVOKED),
    )
    items = result.items if hasattr(result, "items") else result
    return {item.label: item for item in items or []}


@pytest.fixture
def private_keywords_shown(protocol: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    lsp = protocol[0]
    monkeypatch.setattr(
        lsp.robot_completion, "get_config", lambda document: CompletionConfig(hide_private_keywords=False)
    )


# Completion leaves out private keywords of other files


@needs_private
def test_completion_leaves_out_private_keywords_of_an_imported_resource_file(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + TEST_WITH_EMPTY_ROW, 6, 4)

    assert "Public Helper" in items
    assert "Private Helper" not in items
    assert "Doc Private Helper" not in items


@needs_private
def test_completion_after_the_name_of_the_resource_file(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + "*** Test Cases ***\nT\n    helpers.\n", 6, 12)

    assert "Public Helper" in items
    assert "Private Helper" not in items


@needs_private
@pytest.mark.parametrize(("row", "character"), [("    ", 4), ("    PrivLib.", 12)], ids=["no prefix", "library name"])
def test_completion_leaves_out_private_library_keywords(protocol: Any, row: str, character: int) -> None:
    items = _completion(protocol, SUITE_HEADER + f"*** Test Cases ***\nT\n{row}\n    No Operation\n", 6, character)

    assert "Lib Public" in items
    assert "Lib Private" not in items


@pytest.mark.skipif(RF_VERSION >= (6, 0), reason="Robot Framework 6.0 introduced private keywords")
def test_completion_before_robot_framework_60(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + TEST_WITH_EMPTY_ROW, 6, 4)

    assert "Private Helper" in items
    assert items["Private Helper"].label_details is None


# Completion offers private keywords of the current file


def test_completion_in_a_keyword_of_the_resource_file_that_defines_the_keyword(protocol: Any) -> None:
    text = (
        "*** Keywords ***\nUser\n    \n    No Operation\n\nOwn Private\n    [Tags]    robot:private\n    No Operation\n"
    )
    items = _completion(protocol, text, 2, 4, suffix=".resource")

    assert "Own Private" in items
    assert items["Own Private"].label_details is None


def test_completion_in_a_test_case_of_the_suite_file_that_defines_the_keyword(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + TEST_WITH_EMPTY_ROW + OWN_KEYWORDS, 6, 4)

    assert "Own Helper" in items
    assert items["Own Helper"].label_details is None


# Setting for private keywords of other files


def test_setting_not_set(protocol: Any) -> None:
    lsp = protocol[0]
    document, _ = _open(protocol, SUITE_HEADER + TEST_WITH_EMPTY_ROW)

    assert lsp.robot_completion.get_config(document).hide_private_keywords is True


def test_setting_name() -> None:
    assert from_dict({"hidePrivateKeywords": False}, CompletionConfig).hide_private_keywords is False


@needs_private
@pytest.mark.usefixtures("private_keywords_shown")
def test_setting_switched_off(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + TEST_WITH_EMPTY_ROW, 6, 4)

    for name in ("Private Helper", "Doc Private Helper", "Lib Private"):
        details = items[name].label_details
        assert details is not None
        assert details.description == "private"
    assert items["Public Helper"].label_details is None
    assert str(items["Private Helper"].sort_text) > str(items["Public Helper"].sort_text)
    assert str(items["Lib Private"].sort_text) > str(items["Lib Public"].sort_text)


@needs_private
@pytest.mark.usefixtures("private_keywords_shown")
def test_setting_switched_off_after_the_name_of_the_resource_file(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + "*** Test Cases ***\nT\n    helpers.\n", 6, 12)

    assert items["Private Helper"].label_details is not None
    assert str(items["Private Helper"].sort_text) > str(items["Public Helper"].sort_text)
