import asyncio
import dataclasses
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, cast

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
from robotcode.language_server.common.parts.workspace import HasConfigSection
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.configuration import (
    RobotCodeConfig,
    RobotConfig,
)
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.language_server.robotframework.server import RobotLanguageServer
from robotcode.utils.dataclasses import as_dict
from tests.robotcode.language_server.robotframework.tools import generate_test_id


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    try:
        yield loop
    finally:
        loop.close()


@pytest_asyncio.fixture(scope="module", ids=generate_test_id)
@pytest.mark.usefixtures("event_loop")
async def protocol(request: Any) -> AsyncGenerator[RobotLanguageServerProtocol, None]:
    root_path = Path().resolve()
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
        await protocol._initialized(InitializedParams())
        await protocol.workspace._workspace_did_change_configuration(
            {
                cast(HasConfigSection, RobotCodeConfig).__config_section__: as_dict(
                    RobotCodeConfig(
                        robot=RobotConfig(
                            env={"ENV_VAR": "1"},
                            variables={
                                "CMD_VAR": "1",
                            },
                        )
                    )
                )
            }
        )
        yield protocol
    finally:
        await protocol._shutdown()
        server.close()


@pytest_asyncio.fixture(scope="function")
@pytest.mark.usefixtures("event_loop")
async def test_document(request: Any) -> AsyncGenerator[TextDocument, None]:
    data_path = Path(request.param)
    data = data_path.read_text()

    document = TextDocument(
        document_uri=data_path.absolute().as_uri(), language_id="robotframework", version=1, text=data
    )
    try:
        yield document
    finally:
        del document
