"""Deprecated keywords in keyword completion.

Every scenario of the `deprecated-keywords` spec runs on both analysis paths:
the legacy path (flag off) and the SemanticModel (flag on).
"""

import itertools
from pathlib import Path
from typing import Any, Dict, Iterator

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

_file_counter = itertools.count()

OLD_RESOURCE = """\
*** Keywords ***
Click Element
    No Operation

Click Link
    No Operation

Click Old Element
    [Documentation]    *DEPRECATED!* Use Click Element.
    No Operation

Old User Kw
    [Documentation]    *DEPRECATED!* Use something else.
    No Operation

Private Helper
    [Tags]    robot:private
    No Operation
"""

DEP_LIB = '''\
def old_lib_kw():
    """*DEPRECATED* Use New Lib Kw."""


def new_lib_kw():
    pass
'''

SUITE_HEADER = """\
*** Settings ***
Resource    old.resource
Library    DepLib.py

"""


def _test_case(row: str) -> str:
    """A test case whose second row is `row`; that row is row 6 of the suite."""
    return f"*** Test Cases ***\nT\n{row}\n    No Operation\n"


@pytest.fixture(scope="module", params=[False, True], ids=["legacy", "model"])
def protocol(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    root = tmp_path_factory.mktemp("deprecated_keywords")
    # outside the workspace, so the workspace scan at startup never reads a file while it is written
    files = tmp_path_factory.mktemp("deprecated_keywords_files")
    Path(files, "old.resource").write_text(OLD_RESOURCE, encoding="utf-8")
    Path(files, "DepLib.py").write_text(DEP_LIB, encoding="utf-8")

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

    protocol._initialized(InitializedParams())
    assert protocol.diagnostics.workspace_analyzed_event.wait(300), "the workspace analysis did not end"
    try:
        yield protocol, files, request.param
    finally:
        protocol._shutdown()


def _open(protocol: Any, text: str) -> Any:
    lsp, files, semantic_model = protocol
    path = Path(files, f"suite_{next(_file_counter)}.robot")
    path.write_text(text, encoding="utf-8")
    document = lsp.documents.get_or_open_document(path, "robotframework")
    assert (lsp.documents_cache.get_namespace(document).semantic_model is not None) == semantic_model
    return document


def _completion(protocol: Any, text: str, character: int) -> Dict[str, CompletionItem]:
    """The completion items on row 6 of `text` at `character`, by label."""
    lsp = protocol[0]
    result = lsp.robot_completion.collect(
        lsp.robot_completion,
        _open(protocol, text),
        Position(line=6, character=character),
        CompletionContext(trigger_kind=CompletionTriggerKind.INVOKED),
    )
    items = result.items if hasattr(result, "items") else result
    return {item.label: item for item in items or []}


def _use_config(protocol: Any, monkeypatch: pytest.MonkeyPatch, config: CompletionConfig) -> None:
    lsp = protocol[0]
    monkeypatch.setattr(lsp.robot_completion, "get_config", lambda document: config)


# --- Deprecated keywords are marked in every keyword list ---


def test_deprecated_library_keyword_after_the_library_name(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + _test_case("    DepLib."), 11)

    assert items["Old Lib Kw"].deprecated is True
    assert not items["New Lib Kw"].deprecated


def test_deprecated_resource_keyword_after_the_resource_name(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + _test_case("    old."), 8)

    assert items["Click Old Element"].deprecated is True
    assert not items["Click Element"].deprecated


def test_deprecated_resource_keyword_without_a_prefix(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + _test_case("    "), 4)

    assert items["Old User Kw"].deprecated is True
    assert not items["Click Element"].deprecated


# --- Deprecated keywords sort after the other keywords ---


def test_order_in_the_list_without_a_prefix(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + _test_case("    "), 4)

    old = str(items["Click Old Element"].sort_text)
    assert old > str(items["Click Element"].sort_text)
    assert old > str(items["Click Link"].sort_text)


def test_order_after_the_library_name(protocol: Any) -> None:
    items = _completion(protocol, SUITE_HEADER + _test_case("    DepLib."), 11)

    assert str(items["Old Lib Kw"].sort_text) > str(items["New Lib Kw"].sort_text)


@pytest.mark.skipif(RF_VERSION < (6, 0), reason="private keywords need Robot Framework 6.0")
def test_shown_private_keywords_stay_after_the_deprecated_ones(protocol: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(protocol, monkeypatch, CompletionConfig(hide_private_keywords=False))
    items = _completion(protocol, SUITE_HEADER + _test_case("    "), 4)

    assert str(items["Private Helper"].sort_text) > str(items["Click Old Element"].sort_text)


# --- Setting to hide deprecated keywords ---


def test_setting_not_set(protocol: Any) -> None:
    lsp = protocol[0]
    document = _open(protocol, SUITE_HEADER + _test_case("    "))
    items = _completion(protocol, SUITE_HEADER + _test_case("    "), 4)

    assert lsp.robot_completion.get_config(document).hide_deprecated_keywords is False
    assert items["Old User Kw"].deprecated is True


def test_setting_name() -> None:
    assert from_dict({"hideDeprecatedKeywords": True}, CompletionConfig).hide_deprecated_keywords is True


@pytest.mark.parametrize(("row", "character"), [("    ", 4), ("    DepLib.", 11)], ids=["no prefix", "library name"])
def test_setting_switched_on(protocol: Any, monkeypatch: pytest.MonkeyPatch, row: str, character: int) -> None:
    _use_config(protocol, monkeypatch, CompletionConfig(hide_deprecated_keywords=True))
    items = _completion(protocol, SUITE_HEADER + _test_case(row), character)

    assert "Old User Kw" not in items
    assert "Old Lib Kw" not in items
    assert "Click Old Element" not in items
    assert "New Lib Kw" in items


def test_deprecated_keyword_of_the_file_being_edited(protocol: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _use_config(protocol, monkeypatch, CompletionConfig(hide_deprecated_keywords=True))
    own = "\n*** Keywords ***\nOwn Old Kw\n    [Documentation]    *DEPRECATED* Gone.\n    No Operation\n"
    items = _completion(protocol, SUITE_HEADER + _test_case("    ") + own, 4)

    assert "Own Old Kw" not in items
    assert "Click Element" in items
