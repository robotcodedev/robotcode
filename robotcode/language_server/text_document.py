import asyncio
import io
import weakref
from typing import List, Optional, overload

from ..utils.logging import LoggingDescriptor
from ..utils.uri import Uri
from .types import DocumentUri, Position, Range, TextDocumentItem


def _utf16_unit_offset(chars: str) -> int:
    return sum(ord(ch) > 0xFFFF for ch in chars)


def _position_from_utf16(lines: List[str], position: Position) -> Position:
    # see: https://github.com/microsoft/language-server-protocol/issues/376

    try:
        return Position(
            line=position.line,
            character=position.character - _utf16_unit_offset(lines[position.line][: position.character]),
        )
    except IndexError:
        return Position(line=len(lines), character=0)


def _range_from_utf16(lines: List[str], range: Range) -> Range:
    return Range(start=_position_from_utf16(lines, range.start), end=_position_from_utf16(lines, range.end))


class TextDocument:
    _logger = LoggingDescriptor()

    @overload
    def __init__(
        self,
        text_document: TextDocumentItem,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        *,
        document_uri: DocumentUri,
        language_id: str,
        version: int,
        text: str,
        parent: Optional["TextDocument"] = None,
    ) -> None:
        ...

    def __init__(
        self,
        text_document: Optional[TextDocumentItem] = None,
        *,
        document_uri: Optional[DocumentUri] = None,
        language_id: Optional[str] = None,
        version: Optional[int] = None,
        text: Optional[str] = None,
        parent: Optional["TextDocument"] = None,
    ) -> None:
        super().__init__()

        self._lock = asyncio.Lock()

        self.document_uri = (
            text_document.uri if text_document is not None else document_uri if document_uri is not None else ""
        )
        self.uri = Uri(self.document_uri)

        self.language_id = (
            text_document.language_id if text_document is not None else language_id if language_id is not None else ""
        )
        self.version = text_document.version if text_document is not None else version if version is not None else -1
        self._text = text_document.text if text_document is not None else text if text is not None else ""

        self._parent: Optional[weakref.ReferenceType[TextDocument]] = None
        if parent is not None:
            self._parent = weakref.ref(parent)

    @property
    def parent(self) -> Optional["TextDocument"]:
        if self._parent is None:
            return None

        return self._parent()

    def freeze(self) -> "TextDocument":
        return TextDocument(
            document_uri=self.document_uri,
            language_id=self.language_id,
            version=self.version,
            text=self.text,
            parent=self,
        )

    async def freeze_async(self) -> "TextDocument":
        async with self._lock:
            return self.freeze()

    def __str__(self) -> str:
        return super().__str__()

    def __repr__(self) -> str:
        return (
            f"TextDocument(uri={repr(self.uri)}, "
            f"language_id={repr(self.language_id)}, "
            f"version={repr(self.version)}, "
            f"text={repr(self.text) if len(self.text)<10 else repr(self.text[:10]+'...')})"
        )

    @property
    def text(self) -> str:
        return self._text

    async def apply_none_change(self) -> None:
        pass

    async def apply_full_change(self, version: Optional[int], text: str) -> None:
        async with self._lock:
            if version is not None:
                self.version = version
            self._text = text

    async def apply_incremental_change(self, version: Optional[int], range: Range, text: str) -> None:
        async with self._lock:
            if version is not None:
                self.version = version

            lines = self.lines
            (start_line, start_col), (end_line, end_col) = _range_from_utf16(lines, range)

            if start_line == len(lines):
                self._text = self._text + text
                return

            new = io.StringIO()

            for i, line in enumerate(lines):
                if i < start_line:
                    new.write(line)
                    continue

                if i > end_line:
                    new.write(line)
                    continue

                if i == start_line:
                    new.write(line[:start_col])
                    new.write(text)

                if i == end_line:
                    new.write(line[end_col:])

            self._text = new.getvalue()

    @property
    def lines(self) -> List[str]:
        return self.text.splitlines(True)
