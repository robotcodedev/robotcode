import os
from pathlib import Path
from typing import Any, List, Optional

from pytest_mock import MockerFixture

from robotcode.core.documents_manager import DocumentsManager
from robotcode.core.uri import Uri
from robotcode.core.utils.path import RACY_MTIME_EPSILON_NS


def _backdate(path: Path, ns: int = RACY_MTIME_EPSILON_NS * 5) -> None:
    t = os.stat(path).st_mtime_ns - ns
    os.utime(path, ns=(t, t))


class _FileReader:
    """on_read_document_text subscriber that can mutate the file while reading.

    ``mutate_on_reads`` holds texts that are written to the file *after* the
    corresponding read, simulating a concurrent writer between the two stat
    calls of the verify protocol.
    """

    def __init__(self, mutate_on_reads: Optional[List[str]] = None) -> None:
        self.read_count = 0
        self._mutate_on_reads = mutate_on_reads or []

    def __call__(self, sender: Any, uri: Uri) -> Optional[str]:
        path = uri.to_path()
        text = path.read_text("utf-8")
        if self.read_count < len(self._mutate_on_reads):
            path.write_text(self._mutate_on_reads[self.read_count], "utf-8")
        self.read_count += 1
        return text


# Note: events hold only weak references to their listeners, so every test
# must keep the reader alive in a local variable for the duration of the test.
def _make_manager(reader: _FileReader) -> DocumentsManager:
    manager = DocumentsManager([])
    manager.on_read_document_text.add(reader)
    return manager


def test_settled_file_returns_trusted_info(tmp_path: Path) -> None:
    file = tmp_path / "a.robot"
    file.write_text("content")
    _backdate(file)
    reader = _FileReader()
    manager = _make_manager(reader)

    text, info = manager.read_document_text_with_disk_info(Uri.from_path(file), None)

    assert text == "content"
    assert info is not None
    assert info == manager.get_or_open_document(file).disk_info
    assert info.trusted is True


def test_fresh_file_returns_untrusted_info(tmp_path: Path, mocker: MockerFixture) -> None:
    file = tmp_path / "a.robot"
    file.write_text("content")
    # Freeze "now" right after the file's mtime so the test cannot flake when
    # a stalled runner lets more than the racy epsilon pass before the read.
    time_mock = mocker.patch("robotcode.core.utils.path.time")
    time_mock.time_ns.return_value = os.stat(file).st_mtime_ns + 1
    reader = _FileReader()
    manager = _make_manager(reader)

    text, info = manager.read_document_text_with_disk_info(Uri.from_path(file), None)

    assert text == "content"
    assert info is not None
    assert info.trusted is False


def test_change_during_read_retries_and_returns_settled_state(tmp_path: Path) -> None:
    file = tmp_path / "a.robot"
    file.write_text("first")
    _backdate(file)
    reader = _FileReader(mutate_on_reads=["changed!"])
    manager = _make_manager(reader)

    text, info = manager.read_document_text_with_disk_info(Uri.from_path(file), None)

    assert reader.read_count == 2
    assert text == "changed!"
    assert info is not None
    assert info.size == len("changed!")


def test_file_that_never_settles_returns_no_info(tmp_path: Path) -> None:
    file = tmp_path / "a.robot"
    file.write_text("v0")
    # every read is followed by another write with a different size
    reader = _FileReader(mutate_on_reads=["v0" + "x" * (i + 1) for i in range(10)])
    manager = _make_manager(reader)

    text, info = manager.read_document_text_with_disk_info(Uri.from_path(file), None)

    assert info is None
    assert text.startswith("v0")


def test_unreadable_path_returns_no_info(tmp_path: Path) -> None:
    missing = tmp_path / "missing.robot"
    manager = DocumentsManager([])

    def reader(sender: Any, uri: Uri) -> Optional[str]:
        return "in-memory text"

    manager.on_read_document_text.add(reader)

    text, info = manager.read_document_text_with_disk_info(Uri.from_path(missing), None)

    assert text == "in-memory text"
    assert info is None


def test_get_or_open_document_attaches_disk_info(tmp_path: Path) -> None:
    file = tmp_path / "a.robot"
    file.write_text("content")
    _backdate(file)
    reader = _FileReader()
    manager = _make_manager(reader)

    document = manager.get_or_open_document(file)

    assert document.version is None
    assert document.disk_info is not None
    assert document.disk_info.size == len("content")
    assert document.disk_info.trusted is True
