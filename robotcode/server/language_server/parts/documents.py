from typing import Any, Callable, TYPE_CHECKING, Dict, List, Optional

from ....utils.logging import LoggingDescriptor
from ....utils.async_event import AsyncEvent
from ...jsonrpc2.protocol import GenericJsonRPCProtocolPart, JsonRPCException, rpc_method
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

from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

__all__ = ["TextDocumentProtocolPart", "LanguageServerDocumentException"]


class LanguageServerDocumentException(JsonRPCException):
    pass


class TextDocumentProtocolPart(GenericJsonRPCProtocolPart["LanguageServerProtocol"]):

    _logger = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}
        self.did_open_event = AsyncEvent[Callable[["TextDocumentProtocolPart", TextDocument], Any]]()
        self.did_close_event = AsyncEvent[Callable[["TextDocumentProtocolPart", TextDocument], Any]]()
        self.did_change_event = AsyncEvent[Callable[["TextDocumentProtocolPart", TextDocument], Any]]()
        self.did_save_event = AsyncEvent[Callable[["TextDocumentProtocolPart", TextDocument], Any]]()

    @rpc_method(name="textDocument/didOpen", param_type=DidOpenTextDocumentParams)
    @_logger.call
    async def _text_document_did_open(self, text_document: TextDocumentItem, *args: Any, **kwargs: Any) -> None:
        document = TextDocument(text_document)
        self._documents[text_document.uri] = document

        await self.did_open_event(self, document)

    @rpc_method(name="textDocument/didClose", param_type=DidCloseTextDocumentParams)
    @_logger.call
    async def _text_document_did_close(self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any) -> None:
        document = self._documents.pop(text_document.uri, None)

        self._logger.warning(lambda: f"Document {text_document.uri} is not opened.", condition=lambda: document is None)

        if document is not None:
            await self.did_close_event(self, document)

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
        document = self._documents.get(text_document.uri, None)
        self._logger.warning(lambda: f"Document {text_document.uri} is not opened.", condition=lambda: document is None)

        if document is not None and text is not None:
            await document.apply_full_change(None, text)

        await self.did_save_event(self, document)

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
        document = self._documents.get(text_document.uri, None)
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

        await self.did_change_event(self, document)
