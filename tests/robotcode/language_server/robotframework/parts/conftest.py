import dataclasses
import shutil
from pathlib import Path
from typing import Iterator

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


@pytest.fixture(scope="module", ids=generate_test_id)
def protocol(
    request: pytest.FixtureRequest,
) -> Iterator[RobotLanguageServerProtocol]:
    server = RobotLanguageServer()

    client_capas = ClientCapabilities(
        text_document=TextDocumentClientCapabilities(
            hover=HoverClientCapabilities(content_format=[MarkupKind.MARKDOWN, MarkupKind.PLAIN_TEXT]),
            folding_range=FoldingRangeClientCapabilities(range_limit=0, line_folding_only=False),
        )
    )

    initialization_options = {"python_path": ["./lib", "./resources"]}

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

    # diagnostics_end = threading.Event()

    # def on_diagnostics_end(sender: Any) -> None:
    #     diagnostics_end.set()

    # protocol.diagnostics.on_workspace_diagnostics_end.add(on_diagnostics_end)

    # diagnostics_end.wait(120)
    # protocol.diagnostics.cancel_workspace_diagnostics_task(None)

    protocol.diagnostics.workspace_diagnostics_started_event.wait(300)
    protocol.diagnostics.in_get_workspace_diagnostics_event.wait(300)

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
def regtest(request: pytest.FixtureRequest) -> RegTestFixtureEx:
    return RegTestFixtureEx(request)
