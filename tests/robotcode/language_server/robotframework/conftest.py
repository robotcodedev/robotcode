import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, cast

import pytest

from robotcode.language_server.common.lsp_types import (
    ClientCapabilities,
    ClientInfo,
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


@pytest.fixture(scope="function")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    logging.info("create event_loop")
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        for t in asyncio.all_tasks(loop):
            logging.error(t)

        logging.info("event_loop close")

        # loop.close()

        logging.info("event_loop closed")


@pytest.fixture(scope="function")
async def protocol(event_loop: asyncio.AbstractEventLoop) -> AsyncGenerator[RobotLanguageServerProtocol, None]:
    root_path = Path().resolve()
    server = RobotLanguageServer()
    try:
        protocol = RobotLanguageServerProtocol(server)
        await protocol._initialize(
            ClientCapabilities(
                text_document=TextDocumentClientCapabilities(
                    hover=HoverClientCapabilities(content_format=[MarkupKind.MARKDOWN, MarkupKind.PLAINTEXT])
                )
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
        server.close()


@pytest.fixture(scope="function")
async def test_document(event_loop: asyncio.AbstractEventLoop, request: Any) -> AsyncGenerator[TextDocument, None]:
    data_path = Path(request.param)
    data = data_path.read_text()

    document = TextDocument(
        document_uri=data_path.absolute().as_uri(), language_id="robotframework", version=1, text=data
    )
    try:
        yield document
    finally:
        # del document
        pass
