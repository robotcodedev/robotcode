import dataclasses
from pathlib import Path
from typing import Any, AsyncIterator, cast

import pytest
import pytest_asyncio

from robotcode.language_server.common.lsp_types import (
    ClientCapabilities,
    ClientInfo,
    FoldingRangeClientCapabilities,
    HoverClientCapabilities,
    InitializedParams,
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
from robotcode.utils.dataclasses import as_dict
from tests.robotcode.language_server.robotframework.tools import generate_test_id

from .pytest_regtestex import RegTestFixtureEx


@pytest_asyncio.fixture(scope="package", ids=generate_test_id)
async def protocol(request: Any) -> AsyncIterator[RobotLanguageServerProtocol]:
    root_path = Path(Path(__file__).resolve().parent, "data")

    server = RobotLanguageServer()
    try:
        client_capas = ClientCapabilities(
            text_document=TextDocumentClientCapabilities(
                hover=HoverClientCapabilities(content_format=[MarkupKind.MARKDOWN, MarkupKind.PLAINTEXT]),
                folding_range=FoldingRangeClientCapabilities(range_limit=0, line_folding_only=False),
            )
        )

        protocol = RobotLanguageServerProtocol(server)
        await protocol._initialize(
            dataclasses.replace(
                client_capas,
                **(
                    {k: v for k, v in vars(request.param).items() if v is not None} if hasattr(request, "param") else {}
                ),
            ),
            root_path=str(root_path),
            root_uri=root_path.as_uri(),
            workspace_folders=[WorkspaceFolder(name="test workspace", uri=root_path.as_uri())],
            client_info=ClientInfo(name="TestClient", version="1.0.0"),
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
                )
            )
        }

        await protocol._initialized(InitializedParams())

        yield protocol
    finally:
        await protocol._shutdown()
        server.close()


@pytest_asyncio.fixture(scope="module")
@pytest.mark.usefixtures("event_loop")
async def test_document(request: Any) -> AsyncIterator[TextDocument]:
    data_path = Path(request.param)
    data = data_path.read_text()

    document = TextDocument(
        document_uri=data_path.absolute().as_uri(), language_id="robotframework", version=1, text=data
    )
    try:
        yield document
    finally:
        del document


@pytest.fixture()
def regtest(request: Any) -> RegTestFixtureEx:
    item = request.node

    return RegTestFixtureEx(request, item.nodeid)
