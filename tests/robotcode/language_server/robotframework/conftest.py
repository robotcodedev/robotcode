import asyncio
from pathlib import Path
from typing import Any, AsyncGenerator, Generator

import pytest
import pytest_asyncio

from robotcode.language_server.common.text_document import TextDocument


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    try:
        yield loop
    finally:
        loop.close()


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
