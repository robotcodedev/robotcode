import dataclasses
from pathlib import Path
from typing import Any, AsyncGenerator, cast

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


@pytest_asyncio.fixture(scope="module", ids=generate_test_id)
@pytest.mark.usefixtures("event_loop")
async def protocol(request: Any) -> AsyncGenerator[RobotLanguageServerProtocol, None]:
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
        await protocol._initialized(InitializedParams())
        await protocol.workspace._workspace_did_change_configuration(
            {
                cast(HasConfigSection, RobotCodeConfig).__config_section__: as_dict(
                    RobotCodeConfig(
                        robot=RobotConfig(
                            python_path=["./lib", "./resources"],
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
