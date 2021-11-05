import asyncio
from asyncio.events import AbstractEventLoop
from typing import Generator

import pytest

from robotcode.language_server.common.lsp_types import Position, Range
from robotcode.language_server.common.text_document import (
    InvalidRangeError,
    TextDocument,
)


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
    text = """\
first line
second line
third"""
    new_text = """changed """
    expected = """\
first line
second changed line
third"""

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    await document.apply_incremental_change(
        1, Range(start=Position(line=1, character=7), end=Position(line=1, character=7)), new_text
    )

    assert document.text == expected


@pytest.mark.asyncio
async def test_apply_apply_incremental_change_with_start_line_eq_len_lines_should_work() -> None:
    text = """\
first line
second line
third"""
    new_text = """changed """

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    await document.apply_incremental_change(
        1, Range(start=Position(line=3, character=7), end=Position(line=3, character=8)), new_text
    )

    assert document.text == text + new_text


@pytest.mark.asyncio
async def test_apply_apply_incremental_change_with_wrong_range_should_raise_invalidrangerrror() -> None:
    text = """first"""
    new_text = """changed"""

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    with pytest.raises(InvalidRangeError):
        await document.apply_incremental_change(
            1, Range(start=Position(line=4, character=len(text)), end=Position(line=0, character=len(text))), new_text
        )


@pytest.mark.asyncio
async def test_apply_none_change_should_work() -> None:
    text = """first"""

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    await document.apply_none_change()

    assert document.text == text


@pytest.mark.asyncio
async def test_lines_should_give_the_lines_of_the_document() -> None:
    text = """\
first
second
third
"""

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    assert document.text == text

    await document.apply_none_change()

    assert document.lines == text.splitlines(True)


class WeakReferencable:
    pass


@pytest.mark.asyncio
async def test_document_get_set_clear_data_should_work() -> None:
    text = """\
first
second
third
"""
    key = WeakReferencable()
    data = "some data"

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)
    document.set_data(key, data)

    assert document.get_data(key) == data
    await document.clear()
    assert document.get_data(key, None) is None


@pytest.mark.asyncio
async def test_document_get_set_cache_with_function_should_work() -> None:
    text = """\
first
second
third
"""

    async def get_data(document: TextDocument, data: str) -> str:
        return "blah" + data

    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)

    assert await document.get_cache(get_data, "data") == "blahdata"

    await document.remove_cache_entry(get_data)


@pytest.mark.asyncio
async def test_document_get_set_cache_with_method_should_work() -> None:
    text = """\
first
second
third
"""
    document = TextDocument(document_uri="file://test.robot", language_id="robotframework", version=1, text=text)

    class Dummy:
        async def get_data(self, document: TextDocument, data: str) -> str:
            return "blah" + data

    dummy = Dummy()

    assert await document.get_cache(dummy.get_data, "data") == "blahdata"

    # await document.remove_cache_entry(dummy.get_data)
    del dummy
