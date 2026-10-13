"""Tests for the file-watcher re-read path of TextDocumentProtocolPart.

A CHANGED event for a document that is not open in the editor must re-read
the text from disk and attach the matching DiskInfo snapshot, so the
analysis caches can persist state derived from that content.

Closing a document the editor had open must leave it with the text that was
saved last, not with the text it had before it was edited.
"""

from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from robotcode.core.lsp.types import (
    FileChangeType,
    FileEvent,
    TextDocumentContentChangeEventType2,
    TextDocumentIdentifier,
    TextDocumentItem,
    TextDocumentSyncKind,
    VersionedTextDocumentIdentifier,
)
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


def _open_and_edit(part: TextDocumentProtocolPart, file: Path, text: str) -> str:
    uri = str(Uri.from_path(file))
    part.parent.capabilities.text_document_sync = TextDocumentSyncKind.FULL

    part._text_document_did_open(
        TextDocumentItem(uri=uri, language_id="robotframework", version=1, text=file.read_text("utf-8"))
    )
    part._text_document_did_change(
        VersionedTextDocumentIdentifier(uri=uri, version=2), [TextDocumentContentChangeEventType2(text=text)]
    )

    return uri


@pytest.mark.parametrize("sent_text", ["new content", None], ids=["with text", "without text"])
def test_closing_a_saved_document_keeps_the_saved_text(tmp_path: Path, sent_text: Optional[str]) -> None:
    file = tmp_path / "a.robot"
    file.write_text("old content", "utf-8")

    part = _make_part()
    part.on_read_document_text.add(_reader)

    document = part.get_or_open_document(file)
    uri = _open_and_edit(part, file, "new content")

    file.write_text("new content", "utf-8")
    part._text_document_did_save(TextDocumentIdentifier(uri=uri), sent_text)
    part._text_document_did_close(TextDocumentIdentifier(uri=uri))

    assert document.text() == "new content"


def test_closing_a_document_drops_its_unsaved_changes(tmp_path: Path) -> None:
    file = tmp_path / "a.robot"
    file.write_text("old content", "utf-8")

    part = _make_part()
    part.on_read_document_text.add(_reader)

    document = part.get_or_open_document(file)
    uri = _open_and_edit(part, file, "unsaved content")

    part._text_document_did_close(TextDocumentIdentifier(uri=uri))

    assert document.text() == "old content"
