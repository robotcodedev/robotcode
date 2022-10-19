import asyncio
from typing import Generator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    import asyncio.runners

    loop = asyncio.new_event_loop()
    # loop.set_debug(True)
    try:
        yield loop
    finally:
        loop.close()
