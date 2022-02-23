import asyncio
from typing import Generator

import pytest


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    loop.set_debug(True)
    try:
        yield loop
    finally:
        loop.close()
