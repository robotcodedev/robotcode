from pathlib import Path
from typing import AsyncGenerator

import pytest

from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.common.types import (
    ClientCapabilities,
    ClientInfo,
    HoverClientCapabilities,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    TextDocumentClientCapabilities,
    WorkspaceFolder,
)
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.language_server.robotframework.server import RobotLanguageServer


@pytest.fixture
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

        yield protocol
    finally:
        server.close()


@pytest.fixture
async def test_document() -> AsyncGenerator[TextDocument, None]:
    data = """\
***Test Cases***
first
    Log  Hello
"""
    yield TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=data)


@pytest.mark.parametrize(
    ("position",),
    [
        (Position(line=2, character=4),),
        (Position(line=2, character=5),),
        (Position(line=2, character=6),),
    ],
)
@pytest.mark.asyncio
async def test_hover_should_find_simple_keyword(
    protocol: RobotLanguageServerProtocol, test_document: TextDocument, position: Position
) -> None:

    result = await protocol._robot_hover.collect(protocol.hover, test_document, position)
    assert result
    assert result.range == Range(start=Position(line=2, character=4), end=Position(line=2, character=7))
    assert isinstance(result.contents, MarkupContent)
    assert result.contents.kind == MarkupKind.MARKDOWN
    assert "Log" in result.contents.value


@pytest.mark.parametrize(
    ("position",),
    [
        (Position(line=2, character=3),),
        (Position(line=2, character=7),),
    ],
)
@pytest.mark.asyncio
async def test_hover_should_not_find_simple_keyword_on_boundaries(
    protocol: RobotLanguageServerProtocol, test_document: TextDocument, position: Position
) -> None:

    result = await protocol._robot_hover.collect(protocol.hover, test_document, position)
    assert result is None
