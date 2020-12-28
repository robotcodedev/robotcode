import io
from typing import Optional, TYPE_CHECKING, Dict, List

from ..utils.logging import LoggingDescriptor
from .jsonrpc2_server import (
    GenericJsonRPCProtocolPart,
    JsonRPCException,
    rpc_method,
)
from .types import (
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentUri,
    Position,
    Range,
    TextDocumentContentChangeEvent,
    TextDocumentContentRangeChangeEvent,
    TextDocumentContentTextChangeEvent,
    TextDocumentIdentifier,
    TextDocumentItem,
    TextDocumentSaveReason,
    TextDocumentSyncKind,
    TextDocumentSyncOptions,
    TextEdit,
    VersionedTextDocumentIdentifier,
    WillSaveTextDocumentParams,
)

if TYPE_CHECKING:
    from .language_server import LanguageServerProtocol

__all__ = ["TextDocumentProtocolPart"]


class LanguageServerDocumentException(JsonRPCException):
    pass


def _utf16_unit_offset(chars: str):
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

    def __init__(
        self,
        text_document: TextDocumentItem,
    ) -> None:
        super().__init__()

        self.uri = text_document.uri
        self.language_id = text_document.language_id
        self.version = text_document.version
        self.text = text_document.text

    def apply_none_change(self):
        pass

    def apply_full_change(self, version, text: str):
        self.version = version
        self.text = text

    def apply_incremental_change(self, version, range: Range, text: str):
        self.version = version
        lines = self.lines
        (start_line, start_col), (end_line, end_col) = _range_from_utf16(lines, range)

        if start_line == len(lines):
            self.text = self.text + text
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

        self.text = new.getvalue()

    @property
    def lines(self) -> List[str]:
        return self.text.splitlines(True)


class TextDocumentProtocolPart(GenericJsonRPCProtocolPart["LanguageServerProtocol"]):

    _logger = LoggingDescriptor()

    def __init__(self, protocol: "LanguageServerProtocol") -> None:
        super().__init__(protocol)
        self._documents: Dict[DocumentUri, TextDocument] = {}

    @rpc_method(name="textDocument/didOpen", param_type=DidOpenTextDocumentParams)
    @_logger.call
    async def _text_document_did_open(self, text_document: TextDocumentItem, *args, **kwargs):
        self._documents[text_document.uri] = TextDocument(text_document)

    @rpc_method(name="textDocument/didClose", param_type=DidCloseTextDocumentParams)
    @_logger.call
    async def _text_document_did_close(self, text_document: TextDocumentIdentifier, *args, **kwargs):
        document = self._documents.pop(text_document.uri, None)

        self._logger.warning(lambda: f"Document {text_document.uri} is not opened.", condition=lambda: document is None)

    @rpc_method(name="textDocument/willSave", param_type=WillSaveTextDocumentParams)
    @_logger.call
    async def _text_document_will_save(
        self, text_document: TextDocumentIdentifier, reason: TextDocumentSaveReason, *args, **kwargs
    ):
        pass

    @rpc_method(name="textDocument/didSave", param_type=DidSaveTextDocumentParams)
    @_logger.call
    async def _text_document_did_save(
        self, text_document: TextDocumentIdentifier, text: Optional[str] = None, *args, **kwargs
    ):
        pass

    @rpc_method(name="textDocument/willSaveWaitUntil", param_type=WillSaveTextDocumentParams)
    @_logger.call
    async def _text_document_will_save_wait_until(
        self, text_document: TextDocumentIdentifier, reason: TextDocumentSaveReason, *args, **kwargs
    ) -> List[TextEdit]:
        return []

    @rpc_method(name="textDocument/didChange", param_type=DidChangeTextDocumentParams)
    @_logger.call
    async def _text_document_did_change(
        self,
        text_document: VersionedTextDocumentIdentifier,
        content_changes: List[TextDocumentContentChangeEvent],
        *args,
        **kwargs,
    ):
        document = self._documents.get(text_document.uri, None)
        if document is None:
            raise LanguageServerDocumentException(f"Document {text_document.uri} is not opened.")

        sync_kind = (
            self.protocol.capabilities.text_document_sync
            if isinstance(self.protocol.capabilities.text_document_sync, TextDocumentSyncKind)
            else self.protocol.capabilities.text_document_sync.change
            if isinstance(self.protocol.capabilities.text_document_sync, TextDocumentSyncOptions)
            else None
        )
        for content_change in content_changes:
            if sync_kind is None or sync_kind == TextDocumentSyncKind.NONE:
                # do nothing
                document.apply_none_change()
            elif sync_kind == TextDocumentSyncKind.FULL and isinstance(
                content_change, TextDocumentContentTextChangeEvent
            ):
                document.apply_full_change(text_document.version, content_change.text)
            elif sync_kind == TextDocumentSyncKind.INCREMENTAL and isinstance(
                content_change, TextDocumentContentRangeChangeEvent
            ):
                document.apply_incremental_change(text_document.version, content_change.range, content_change.text)
            else:
                raise LanguageServerDocumentException(
                    f"Invalid type for content_changes {type(content_change)} "
                    f"and server capability {self.protocol.capabilities.text_document_sync} "
                    f"for document {text_document.uri}."
                )
