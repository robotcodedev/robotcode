"""Tests for the file-watcher re-read path of TextDocumentProtocolPart.

A CHANGED event for a document that is not open in the editor must re-read
the text from disk and attach the matching DiskInfo snapshot, so the
analysis caches can persist state derived from that content.
"""

from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock

from robotcode.core.lsp.types import FileChangeType, FileEvent
from robotcode.core.uri import Uri
from robotcode.language_server.common.parts.documents import TextDocumentProtocolPart


def _make_part() -> TextDocumentProtocolPart:
    parent = MagicMock()
    parent.language_definitions = []
    return TextDocumentProtocolPart(parent)


def _reader(sender: Any, uri: Uri) -> Optional[str]:
    return uri.to_path().read_text("utf-8")


def test_changed_event_rereads_document_and_attaches_disk_info(tmp_path: Path) -> None:
    file = tmp_path / "a.robot"
    file.write_text("old content", "utf-8")

    part = _make_part()
    part.on_read_document_text.add(_reader)

    document = part.get_or_open_document(file)
    assert document.text() == "old content"

    file.write_text("new content!", "utf-8")

    part._file_watcher(None, [FileEvent(uri=str(Uri.from_path(file)), type=FileChangeType.CHANGED)])

    assert document.text() == "new content!"
    assert document.disk_info is not None
    assert document.disk_info.size == len("new content!")


def test_changed_event_ignores_documents_open_in_editor(tmp_path: Path) -> None:
    file = tmp_path / "a.robot"
    file.write_text("old content", "utf-8")

    part = _make_part()
    part.on_read_document_text.add(_reader)

    document = part.get_or_open_document(file)
    document.opened_in_editor = True

    file.write_text("new content!", "utf-8")

    part._file_watcher(None, [FileEvent(uri=str(Uri.from_path(file)), type=FileChangeType.CHANGED)])

    assert document.text() == "old content"
