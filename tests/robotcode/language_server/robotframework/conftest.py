import asyncio
from typing import Iterator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    import asyncio.runners

    loop = asyncio.new_event_loop()
    # loop.set_debug(True)
    try:
        yield loop
    finally:
        loop.close()
