import asyncio
from asyncio.events import AbstractEventLoop
from typing import Generator

import pytest

from robotcode.language_server.text_document import TextDocument
from robotcode.language_server.types import Position, Range


@pytest.fixture
def event_loop() -> Generator[AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_apply_full_change_should_work() -> None:
    text = """first"""
    new_text = """changed"""
    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    await document.apply_full_change(1, new_text)

    assert document.text == new_text


@pytest.mark.asyncio
async def test_apply_apply_incremental_change_at_begining_should_work() -> None:
    text = """first"""
    new_text = """changed"""
    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    await document.apply_incremental_change(
        1, Range(start=Position(line=0, character=0), end=Position(line=0, character=0)), new_text
    )

    assert document.text == new_text + text


@pytest.mark.asyncio
async def test_apply_apply_incremental_change_at_end_should_work() -> None:
    text = """first"""
    new_text = """changed"""

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    await document.apply_incremental_change(
        1, Range(start=Position(line=0, character=len(text)), end=Position(line=0, character=len(text))), new_text
    )

    assert document.text == text + new_text


@pytest.mark.asyncio
async def test_apply_apply_incremental_change_in_the_middle_should_work() -> None:
    text = """first"""
    new_text = """changed"""

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    await document.apply_incremental_change(
        1, Range(start=Position(line=0, character=len(text)), end=Position(line=0, character=len(text))), new_text
    )

    assert document.text == text + new_text
