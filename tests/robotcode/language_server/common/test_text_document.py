import pytest
from robotcode.core.lsp.types import Position, Range
from robotcode.language_server.common.text_document import (
    InvalidRangeError,
    TextDocument,
)


def test_apply_full_change_should_work() -> None:
    text = """first"""
    new_text = """changed"""
    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    document.apply_full_change(1, new_text)

    assert document.text() == new_text


def test_apply_apply_incremental_change_at_begining_should_work() -> None:
    text = """first"""
    new_text = """changed"""
    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    document.apply_incremental_change(
        1, Range(start=Position(line=0, character=0), end=Position(line=0, character=0)), new_text
    )

    assert document.text() == new_text + text


def test_apply_apply_incremental_change_at_end_should_work() -> None:
    text = """first"""
    new_text = """changed"""

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    document.apply_incremental_change(
        1, Range(start=Position(line=0, character=len(text)), end=Position(line=0, character=len(text))), new_text
    )

    assert document.text() == text + new_text


def test_save_and_revert_should_work() -> None:
    text = """first"""
    new_text = """changed"""

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    assert not document.revert(None)

    document.apply_incremental_change(
        2, Range(start=Position(line=0, character=len(text)), end=Position(line=0, character=len(text))), new_text
    )

    assert document.text() == text + new_text
    assert document.version == 2

    assert document.revert(None)
    assert not document.revert(None)

    assert document.text() == text
    assert document.version == 1

    document.apply_incremental_change(
        2, Range(start=Position(line=0, character=len(text)), end=Position(line=0, character=len(text))), new_text
    )

    document.save(None, None)

    assert document.text() == text + new_text
    assert document.version == 2


def test_apply_apply_incremental_change_in_the_middle_should_work() -> None:
    text = """\
first line
second line
third"""
    new_text = """changed """
    expected = """\
first line
second changed line
third"""

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    document.apply_incremental_change(
        1, Range(start=Position(line=1, character=7), end=Position(line=1, character=7)), new_text
    )

    assert document.text() == expected


def test_apply_apply_incremental_change_with_start_line_eq_len_lines_should_work() -> None:
    text = """\
first line
second line
third"""
    new_text = """changed """

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    document.apply_incremental_change(
        1, Range(start=Position(line=3, character=7), end=Position(line=3, character=8)), new_text
    )

    assert document.text() == text + new_text


def test_apply_apply_incremental_change_with_wrong_range_should_raise_invalidrangerrror() -> None:
    text = """first"""
    new_text = """changed"""

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    with pytest.raises(InvalidRangeError):
        document.apply_incremental_change(
            1, Range(start=Position(line=4, character=len(text)), end=Position(line=0, character=len(text))), new_text
        )


def test_apply_none_change_should_work() -> None:
    text = """first"""

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    document.apply_none_change()

    assert document.text() == text


def test_lines_should_give_the_lines_of_the_document() -> None:
    text = """\
first
second
third
"""

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    assert document.text() == text

    document.apply_none_change()

    assert document.get_lines() == text.splitlines(True)


def test_document_get_set_clear_data_should_work() -> None:
    text = """\
first
second
third
"""

    class WeakReferencable:
        pass

    key = WeakReferencable()
    data = "some data"

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)
    document.set_data(key, data)

    assert document.get_data(key) == data
    document.clear()
    assert document.get_data(key, None) is None

    document.set_data(key, data)
    assert document.get_data(key) == data
    document.invalidate_data()
    assert document.get_data(key, None) is None


def test_document_get_set_cache_with_function_should_work() -> None:
    text = """\
first
second
third
"""
    prefix = "1"

    def get_data(document: TextDocument, data: str) -> str:
        return prefix + data

    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)

    assert document.get_cache(get_data, "data") == "1data"

    prefix = "2"
    assert document.get_cache(get_data, "data1") == "1data"

    document.remove_cache_entry(get_data)

    assert document.get_cache(get_data, "data2") == "2data2"

    prefix = "3"
    assert document.get_cache(get_data, "data3") == "2data2"

    document.invalidate_cache()

    assert document.get_cache(get_data, "data3") == "3data3"


def test_document_get_set_cache_with_method_should_work() -> None:
    text = """\
first
second
third
"""
    document = TextDocument(document_uri="file:///test.robot", language_id="robotframework", version=1, text=text)

    prefix = "1"

    class Dummy:
        def get_data(self, document: TextDocument, data: str) -> str:
            return prefix + data

    dummy = Dummy()

    assert document.get_cache(dummy.get_data, "data") == "1data"

    prefix = "2"
    assert document.get_cache(dummy.get_data, "data1") == "1data"

    document.remove_cache_entry(dummy.get_data)

    assert document.get_cache(dummy.get_data, "data2") == "2data2"

    prefix = "3"
    assert document.get_cache(dummy.get_data, "data3") == "2data2"

    document.invalidate_cache()

    assert document.get_cache(dummy.get_data, "data3") == "3data3"

    del dummy

    assert len(document._cache) == 0
