from typing import Optional

from robotcode.core.lsp.types import Position, Range
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.path import DiskInfo


def _make_document(disk_info: Optional[DiskInfo] = None) -> TextDocument:
    return TextDocument(
        document_uri="file:///test.robot",
        text="first\n",
        language_id="robotframework",
        disk_info=disk_info,
    )


def test_constructor_stores_disk_info() -> None:
    info = DiskInfo(1, 2)
    assert _make_document(info).disk_info == info
    assert _make_document(None).disk_info is None


def test_full_change_with_text_clears_disk_info() -> None:
    document = _make_document(DiskInfo(1, 2))

    document.apply_full_change(1, "second\n")

    assert document.disk_info is None


def test_full_change_with_save_sets_given_disk_info() -> None:
    document = _make_document(DiskInfo(1, 2))
    new_info = DiskInfo(3, 4)

    document.apply_full_change(None, "second\n", save=True, disk_info=new_info)

    assert document.disk_info == new_info


def test_save_without_disk_info_clears_it() -> None:
    document = _make_document(DiskInfo(1, 2))

    document.save(None, "second\n")

    assert document.disk_info is None


def test_version_only_change_keeps_disk_info() -> None:
    info = DiskInfo(1, 2)
    document = _make_document(info)

    document.apply_full_change(42, None)

    assert document.disk_info == info


def test_none_change_keeps_disk_info() -> None:
    info = DiskInfo(1, 2)
    document = _make_document(info)

    document.apply_none_change()

    assert document.disk_info == info


def test_incremental_change_clears_disk_info() -> None:
    document = _make_document(DiskInfo(1, 2))

    document.apply_incremental_change(
        1,
        Range(start=Position(line=0, character=0), end=Position(line=0, character=0)),
        "x",
    )

    assert document.disk_info is None


def test_revert_clears_disk_info() -> None:
    document = _make_document(DiskInfo(1, 2))
    document.apply_full_change(1, "second\n")

    assert document.revert(None) is True
    assert document.text() == "first\n"
    assert document.disk_info is None


def test_clear_clears_disk_info() -> None:
    document = _make_document(DiskInfo(1, 2))

    document.clear()

    assert document.disk_info is None
