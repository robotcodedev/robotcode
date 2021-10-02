from __future__ import annotations

import gc
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Mapping, Optional

from ....jsonrpc2.protocol import JsonRPCException, rpc_method
from ....utils.async_event import async_event
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ..text_document import TextDocument
from ..types import (
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentUri,
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
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart

__all__ = ["TextDocumentProtocolPart", "LanguageServerDocumentException"]


class LanguageServerDocumentException(JsonRPCException):
    pass


class TextDocumentProtocolPart(LanguageServerProtocolPart, Mapping[DocumentUri, TextDocument]):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}

    @async_event
    async def did_open(sender, document: TextDocument) -> None:
        ...

    @async_event
    async def did_close(sender, document: TextDocument) -> None:
        ...

    @async_event
    async def did_change(sender, document: TextDocument) -> None:
        ...

    @async_event
    async def did_save(sender, document: TextDocument) -> None:
        ...

    def __getitem__(self, k: str) -> Any:
        return self._documents.__getitem__(str(Uri(k).normalized()))

    def __len__(self) -> int:
        return self._documents.__len__()

    def __iter__(self) -> Iterator[DocumentUri]:
        return self._documents.__iter__()

    def __hash__(self) -> int:
        return id(self)

    def _create_document(
        self,
        text_document_item: Optional[TextDocumentItem] = None,
        *,
        document_uri: Optional[DocumentUri] = None,
        language_id: Optional[str] = None,
        version: Optional[int] = None,
        text: Optional[str] = None,
    ) -> TextDocument:
        return TextDocument(
            text_document_item=text_document_item,
            document_uri=document_uri,
            language_id=language_id,
            version=version,
            text=text,
        )

    def append_document(
        self,
        document_uri: DocumentUri,
        language_id: str,
        text: Optional[str],
        version: Optional[int] = None,
    ) -> TextDocument:
        document = self._create_document(document_uri=document_uri, language_id=language_id, version=version, text=text)

        self._documents[document_uri] = document
        return document

    @rpc_method(name="textDocument/didOpen", param_type=DidOpenTextDocumentParams)
    @_logger.call
    async def _text_document_did_open(self, text_document: TextDocumentItem, *args: Any, **kwargs: Any) -> None:
        uri = str(Uri(text_document.uri).normalized())
        document = self.get(uri, None)

        if document is None:
            document = self._create_document(text_document)

            self._documents[uri] = document
            await self.did_open(self, document)
        else:
            await document.apply_full_change(text_document.version, text_document.text)

        document.references.add(self)

    @rpc_method(name="textDocument/didClose", param_type=DidCloseTextDocumentParams)
    @_logger.call
    async def _text_document_did_close(self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any) -> None:
        uri = str(Uri(text_document.uri).normalized())
        document = self._documents.get(uri, None)

        if document is not None:
            document.references.remove(self)

            await self.close_document(document)

    async def close_document(self, document: TextDocument) -> None:
        if len(document.references) == 0:
            self._documents.pop(str(document.uri), None)

            await self.did_close(self, document)

            await document.clear()
            del document
        else:
            document.version = None

        gc.collect()

    @rpc_method(name="textDocument/willSave", param_type=WillSaveTextDocumentParams)
    @_logger.call
    async def _text_document_will_save(
        self, text_document: TextDocumentIdentifier, reason: TextDocumentSaveReason, *args: Any, **kwargs: Any
    ) -> None:
        pass

    @rpc_method(name="textDocument/didSave", param_type=DidSaveTextDocumentParams)
    @_logger.call
    async def _text_document_did_save(
        self, text_document: TextDocumentIdentifier, text: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> None:
        document = self._documents.get(str(Uri(text_document.uri).normalized()), None)
        self._logger.warning(lambda: f"Document {text_document.uri} is not opened.", condition=lambda: document is None)

        if document is not None and text is not None:
            await document.apply_full_change(None, text)

            await self.did_save(self, document)

    @rpc_method(name="textDocument/willSaveWaitUntil", param_type=WillSaveTextDocumentParams)
    @_logger.call
    async def _text_document_will_save_wait_until(
        self, text_document: TextDocumentIdentifier, reason: TextDocumentSaveReason, *args: Any, **kwargs: Any
    ) -> List[TextEdit]:
        return []

    @rpc_method(name="textDocument/didChange", param_type=DidChangeTextDocumentParams)
    @_logger.call
    async def _text_document_did_change(
        self,
        text_document: VersionedTextDocumentIdentifier,
        content_changes: List[TextDocumentContentChangeEvent],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        document = self._documents.get(str(Uri(text_document.uri).normalized()), None)
        if document is None:
            raise LanguageServerDocumentException(f"Document {text_document.uri} is not opened.")

        sync_kind = (
            self.parent.capabilities.text_document_sync
            if isinstance(self.parent.capabilities.text_document_sync, TextDocumentSyncKind)
            else self.parent.capabilities.text_document_sync.change
            if isinstance(self.parent.capabilities.text_document_sync, TextDocumentSyncOptions)
            else None
        )
        for content_change in content_changes:
            if sync_kind is None or sync_kind == TextDocumentSyncKind.NONE:
                # do nothing
                await document.apply_none_change()
            elif sync_kind == TextDocumentSyncKind.FULL and isinstance(
                content_change, TextDocumentContentTextChangeEvent
            ):
                await document.apply_full_change(text_document.version, content_change.text)
            elif sync_kind == TextDocumentSyncKind.INCREMENTAL and isinstance(
                content_change, TextDocumentContentRangeChangeEvent
            ):
                await document.apply_incremental_change(
                    text_document.version, content_change.range, content_change.text
                )
            else:
                raise LanguageServerDocumentException(
                    f"Invalid type for content_changes {type(content_change)} "
                    f"and server capability {self.parent.capabilities.text_document_sync} "
                    f"for document {text_document.uri}."
                )

        await self.did_change(self, document)
