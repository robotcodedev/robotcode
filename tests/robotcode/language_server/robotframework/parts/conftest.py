import asyncio
import dataclasses
import shutil
from pathlib import Path
from typing import AsyncIterator, Iterator, cast

import pytest
import pytest_asyncio
from robotcode.core.dataclasses import as_dict
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
from robotcode.language_server.common.parts.diagnostics import DiagnosticsMode
from robotcode.language_server.common.parts.workspace import HasConfigSection
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.configuration import AnalysisConfig, RobotCodeConfig, RobotConfig
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.language_server.robotframework.server import RobotLanguageServer

from tests.robotcode.language_server.robotframework.tools import generate_test_id

from .pytest_regtestex import RegTestFixtureEx


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", ids=generate_test_id)
async def protocol(request: pytest.FixtureRequest) -> AsyncIterator[RobotLanguageServerProtocol]:
    root_path = Path(Path(__file__).absolute().parent, "data")
    robotcode_cache_path = root_path / ".robotcode_cache"

    if robotcode_cache_path.exists():
        shutil.rmtree(robotcode_cache_path, ignore_errors=True)

    server = RobotLanguageServer()

    client_capas = ClientCapabilities(
        text_document=TextDocumentClientCapabilities(
            hover=HoverClientCapabilities(content_format=[MarkupKind.MARKDOWN, MarkupKind.PLAIN_TEXT]),
            folding_range=FoldingRangeClientCapabilities(range_limit=0, line_folding_only=False),
        )
    )

    initialization_options = {
        "python_path": ["./lib", "./resources"],
    }

    protocol = RobotLanguageServerProtocol(server)
    protocol._initialize(
        dataclasses.replace(
            client_capas,
            **({k: v for k, v in vars(request.param).items() if v is not None} if hasattr(request, "param") else {}),
        ),
        root_path=str(root_path),
        root_uri=root_path.as_uri(),
        workspace_folders=[WorkspaceFolder(name="test workspace", uri=root_path.as_uri())],
        client_info=InitializeParamsClientInfoType(name="TestClient", version="1.0.0"),
        initialization_options=initialization_options,
    )

    protocol.workspace.settings = {
        cast(HasConfigSection, RobotCodeConfig).__config_section__: as_dict(
            RobotCodeConfig(
                robot=RobotConfig(
                    python_path=["./lib", "./resources"],
                    env={"ENV_VAR": "1"},
                    variables={
                        "CMD_VAR": "1",
                    },
                ),
                analysis=AnalysisConfig(diagnostic_mode=DiagnosticsMode.OFF),
            ),
            encode=False,
        )
    }

    protocol._initialized(InitializedParams())
    try:
        yield protocol
    finally:
        protocol._shutdown()
        server.close()


@pytest.fixture(scope="module")
async def test_document(request: pytest.FixtureRequest) -> AsyncIterator[TextDocument]:
    data_path = Path(request.param)
    data = data_path.read_text("utf-8")

    document = TextDocument(
        document_uri=data_path.absolute().as_uri(), language_id="robotframework", version=1, text=data
    )
    try:
        yield document
    finally:
        del document


@pytest.fixture()
def regtest(request: pytest.FixtureRequest) -> RegTestFixtureEx:
    item = request.node

    return RegTestFixtureEx(request, item.nodeid)
