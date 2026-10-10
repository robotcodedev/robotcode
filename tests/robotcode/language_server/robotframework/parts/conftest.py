import dataclasses
import logging
import shutil
from pathlib import Path
from typing import AsyncIterable, Callable, Iterator, List

import pytest

from robotcode.core.lsp.types import (
    ClientCapabilities,
    FoldingRangeClientCapabilities,
    HoverClientCapabilities,
    InitializedParams,
    InitializeParamsClientInfoType,
    MarkupKind,
    TextDocumentClientCapabilities,
    WorkspaceFolder,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.dataclasses import as_dict
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.robotframework.configuration import (
    AnalysisConfig,
    RobotCodeConfig,
)
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.language_server.robotframework.server import RobotLanguageServer
from robotcode.robot.diagnostics.workspace_config import RobotConfig
from tests.robotcode.language_server.robotframework.tools import generate_test_id

from .pytest_regtestex import RegTestFixtureEx

root_path = Path(Path(__file__).absolute().parent, "data")
robotcode_cache_path = root_path / ".robotcode_cache"

if robotcode_cache_path.exists():
    shutil.rmtree(robotcode_cache_path, ignore_errors=True)


@pytest.fixture(scope="session", ids=generate_test_id)
async def protocol(
    request: pytest.FixtureRequest,
) -> AsyncIterable[RobotLanguageServerProtocol]:
    logging.warning("Starting language server")

    server = RobotLanguageServer()

    client_capas = ClientCapabilities(
        text_document=TextDocumentClientCapabilities(
            hover=HoverClientCapabilities(content_format=[MarkupKind.MARKDOWN, MarkupKind.PLAIN_TEXT]),
            folding_range=FoldingRangeClientCapabilities(range_limit=0, line_folding_only=False),
        )
    )

    initialization_options = {"python_path": ["./lib", "./resources"]}

    protocol = RobotLanguageServerProtocol(server)

    to_replace = {}
    if hasattr(request, "param"):
        for f in dataclasses.fields(request.param):
            v = getattr(request.param, f.name)
            if v is not None:
                to_replace[f.name] = v

    protocol._initialize(
        dataclasses.replace(
            client_capas,
            **to_replace,
        ),
        root_path=str(root_path),
        root_uri=root_path.as_uri(),
        workspace_folders=[WorkspaceFolder(name="test workspace", uri=root_path.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
        initialization_options=initialization_options,
    )

    protocol.workspace.settings = {
        RobotCodeConfig.__config_section__: as_dict(
            RobotCodeConfig(
                robot=RobotConfig(
                    python_path=["./lib", "./resources"],
                    env={"ENV_VAR": "1"},
                    variables={"CMD_VAR": "1"},
                ),
                analysis=AnalysisConfig(diagnostic_mode=DiagnosticsMode.OFF),
            ),
            encode=False,
        )
    }

    protocol._initialized(InitializedParams())

    assert protocol.diagnostics.workspace_analyzed_event.wait(300), "the workspace analysis did not end"

    try:
        yield protocol
    finally:
        protocol._shutdown()
        server.close()


@pytest.fixture(scope="session")
def test_document(request: pytest.FixtureRequest, protocol: RobotLanguageServerProtocol) -> Iterator[TextDocument]:
    data_path = Path(request.param)

    document = protocol.documents.get_or_open_document(data_path, "robotframework")

    try:
        yield document
    finally:
        del document


@pytest.fixture
def open_temp_document(
    protocol: RobotLanguageServerProtocol, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Callable[[Path], TextDocument]]:
    """Callable: `(path) -> TextDocument` for files outside the test workspace.

    A document is opened without a version. The workspace diagnostics analyze a
    document with a version in the background; when that analysis comes after
    the document is closed again, it puts the closed document back into the
    reference index. The namespace disk cache is off during the test, so the
    namespace of a document is still analyzed fresh.

    The protocol is shared by the whole test session, so every document opened
    from the file's directory (the file itself and what it imports) is closed
    again. Otherwise it would show up in the results of later tests, e.g. in
    the workspace symbols.
    """
    monkeypatch.setattr(protocol.documents_cache.analysis_config.cache, "cache_namespaces", False)
    directories: List[Path] = []

    def open_document(path: Path) -> TextDocument:
        directories.append(path.parent)
        return protocol.documents.get_or_open_document(path, "robotframework")

    try:
        yield open_document
    finally:
        for document in list(protocol.documents.documents):
            if any(directory in document.uri.to_path().parents for directory in directories):
                # an analyzed document stays in the reference index, also after it is closed
                protocol.documents_cache.get_project_index(document).remove_file(str(document.uri.to_path()))
                protocol.documents.close_document(document, real_close=True)


@pytest.fixture
def regtest(request: pytest.FixtureRequest) -> RegTestFixtureEx:
    return RegTestFixtureEx(request)
