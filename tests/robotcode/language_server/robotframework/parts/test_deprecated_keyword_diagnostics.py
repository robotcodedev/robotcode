"""The message of the `DeprecatedKeyword` diagnostic.

Every scenario of the `deprecated-keywords` spec about the diagnostic runs on both analysis paths:
the legacy path (flag off) and the SemanticModel (flag on).
"""

import itertools
from pathlib import Path
from typing import Any, Iterator, List

import pytest

from robotcode.core.lsp.types import (
    ClientCapabilities,
    Diagnostic,
    DiagnosticSeverity,
    DiagnosticTag,
    InitializedParams,
    InitializeParamsClientInfoType,
    WorkspaceFolder,
)
from robotcode.core.utils.dataclasses import as_dict
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import AnalysisConfig, RobotCodeConfig
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer

_file_counter = itertools.count()

DEP_LIB = '''\
def after_marker():
    """*DEPRECATED!!* Use `New Kw` instead."""


def plain_marker():
    """*DEPRECATED* Please use `New Kw`."""


def two_paragraphs():
    """*DEPRECATED!!* Use `New Kw`
    instead.

    More documentation.
    """


def star_on_second_line():
    """*DEPRECATED since 2.0,
    use `New Kw`.* Really.
    """


def inside_marker():
    """*DEPRECATED since 2.0. Use `New Kw` instead.*"""


def no_reason():
    """*DEPRECATED*"""
'''

DEP_RESOURCE = """\
*** Keywords ***
Old User Kw
    [Documentation]    *DEPRECATED!!* Use something else.
    No Operation
"""

SUITE_HEADER = """\
*** Settings ***
Library     DepLib.py
Resource    dep.resource

*** Test Cases ***
T
"""


@pytest.fixture(scope="module", params=[False, True], ids=["legacy", "model"])
def protocol(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Iterator[Any]:
    root = tmp_path_factory.mktemp("deprecated_keyword_diagnostics")
    # outside the workspace, so the workspace scan at startup never reads a file while it is written
    files = tmp_path_factory.mktemp("deprecated_keyword_diagnostics_files")
    Path(files, "DepLib.py").write_text(DEP_LIB, encoding="utf-8")
    Path(files, "dep.resource").write_text(DEP_RESOURCE, encoding="utf-8")

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


def _deprecated_diagnostics(protocol: Any, keyword: str) -> List[Diagnostic]:
    lsp, files, semantic_model = protocol
    path = Path(files, f"suite_{next(_file_counter)}.robot")
    path.write_text(f"{SUITE_HEADER}    {keyword}\n", encoding="utf-8")
    document = lsp.documents.get_or_open_document(path, "robotframework")
    namespace = lsp.documents_cache.get_namespace(document)
    assert (namespace.semantic_model is not None) == semantic_model
    return [d for d in namespace.diagnostics if d.code == "DeprecatedKeyword"]


def test_reason_after_the_marker(protocol: Any) -> None:
    diagnostics = _deprecated_diagnostics(protocol, "After Marker")

    assert [d.message for d in diagnostics] == ["Keyword 'After Marker' is deprecated. Use `New Kw` instead."]
    assert diagnostics[0].severity == DiagnosticSeverity.HINT
    assert diagnostics[0].tags == [DiagnosticTag.DEPRECATED]


@pytest.mark.parametrize(
    ("keyword", "message"),
    [
        pytest.param(
            "Plain Marker", "Keyword 'Plain Marker' is deprecated. Please use `New Kw`.", id="marker without text"
        ),
        pytest.param(
            "Old User Kw", "Keyword 'Old User Kw' is deprecated. Use something else.", id="keyword of a resource file"
        ),
        pytest.param(
            "Two Paragraphs", "Keyword 'Two Paragraphs' is deprecated. Use `New Kw`\ninstead.", id="first paragraph"
        ),
        pytest.param(
            "Star On Second Line",
            "Keyword 'Star On Second Line' is deprecated. Really.",
            id="closing asterisk on the second line",
        ),
        pytest.param(
            "Inside Marker",
            "Keyword 'Inside Marker' is deprecated. since 2.0. Use `New Kw` instead.",
            id="reason inside the marker",
        ),
        pytest.param("No Reason", "Keyword 'No Reason' is deprecated.", id="no reason"),
    ],
)
def test_message(protocol: Any, keyword: str, message: str) -> None:
    assert [d.message for d in _deprecated_diagnostics(protocol, keyword)] == [message]
