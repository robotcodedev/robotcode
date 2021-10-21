import asyncio
import re
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Tuple, cast

import pytest

from robotcode.language_server.common.parts.workspace import HasConfigSection
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.common.types import (
    ClientCapabilities,
    ClientInfo,
    HoverClientCapabilities,
    InitializedParams,
    MarkupContent,
    MarkupKind,
    Position,
    TextDocumentClientCapabilities,
    WorkspaceFolder,
)
from robotcode.language_server.robotframework.configuration import (
    RobotCodeConfig,
    RobotConfig,
)
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.language_server.robotframework.server import RobotLanguageServer


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def protocol() -> AsyncGenerator[RobotLanguageServerProtocol, None]:
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
                cast(HasConfigSection, RobotCodeConfig)
                .__config_section__: RobotCodeConfig(
                    robot=RobotConfig(
                        env={"ENV_VAR": "1"},
                        variables={
                            "CMD_VAR": "1",
                        },
                    )
                )
                .dict()
            }
        )
        yield protocol
    finally:
        server.close()


@pytest.fixture(scope="module")
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


TEST_EXPRESSION_LINE = re.compile(r"^\#\s*(?P<position>\^+)\s*(?P<name>[^:]+)\s*:\s*(?P<expression>.+)")


def generate_tests_from_doc(path: str) -> Generator[Tuple[str, str, int, int, str], None, None]:
    file = Path(path)

    current_line = 0
    for line, text in enumerate(file.read_text().splitlines()):

        match = TEST_EXPRESSION_LINE.match(text)
        if match:
            name = match.group("name").strip()
            start, end = match.span("position")
            expression = match.group("expression").strip()
            if name and expression:
                if end - start == 1:
                    yield path, name, current_line, start, expression
                else:
                    yield path, name, current_line, start, expression
                    if end - start > 2:
                        yield path, name, current_line, int(start + (end - start) / 2), expression

                    yield path, name, current_line, end - 1, expression
        else:
            current_line = line


@pytest.mark.parametrize(
    ("test_document", "name", "line", "character", "expression"),
    generate_tests_from_doc(str(Path(Path(__file__).parent, "data/hover.robot").relative_to(Path(".").absolute()))),
    indirect=["test_document"],
)
@pytest.mark.asyncio
async def test_hover(
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    name: str,
    line: int,
    character: int,
    expression: str,
) -> None:
    result = await protocol._robot_hover.collect(
        protocol.hover, test_document, Position(line=line, character=character)
    )

    assert bool(
        eval(
            expression,
            {"re": re},
            {
                "result": result,
                "value": result.contents.value
                if result is not None and isinstance(result.contents, MarkupContent)
                else None,
                "line": line,
                "character": character,
            },
        )
    ), expression
