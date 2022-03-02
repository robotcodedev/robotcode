from __future__ import annotations

import gc
import re
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Union

from ....jsonrpc2.protocol import JsonRPCException, rpc_method
from ....utils.async_tools import Lock, async_tasking_event
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ..decorators import language_id_filter
from ..lsp_types import (
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentUri,
    FileEvent,
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
    WatchKind,
    WillSaveTextDocumentParams,
)
from ..text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import LanguageServerProtocol

from .protocol_part import LanguageServerProtocolPart

__all__ = ["TextDocumentProtocolPart", "LanguageServerDocumentException"]


class LanguageServerDocumentException(JsonRPCException):
    pass


class TextDocumentProtocolPart(LanguageServerProtocolPart):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}
        self.parent.on_initialized.add(self._protocol_initialized)
        self._lock = Lock()

    async def _protocol_initialized(self, sender: Any) -> None:
        await self._update_filewatchers()

    async def _update_filewatchers(self) -> None:
        if self.parent.file_extensions:
            await self.parent.workspace.add_file_watcher(
                self._file_watcher,
                f"**/*.{{{','.join(self.parent.file_extensions)}}}",
                WatchKind.CHANGE | WatchKind.DELETE,
            )

    async def _file_watcher(self, sender: Any, changes: List[FileEvent]) -> None:
        to_change: Dict[str, FileEvent] = {}
        for change in changes:
            to_change[change.uri] = change

        for change in to_change.values():
            document = self._documents.get(DocumentUri(Uri(change.uri).normalized()), None)
            if document is not None and not document.opened_in_editor:
                await self.close_document(document, True)
                await self.did_close(self, document, callback_filter=language_id_filter(document))

    @async_tasking_event
    async def did_open(sender, document: TextDocument) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def did_close(sender, document: TextDocument) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def did_change(sender, document: TextDocument) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def did_save(sender, document: TextDocument) -> None:  # NOSONAR
        ...

    async def get(self, _uri: Union[DocumentUri, Uri]) -> Optional[TextDocument]:
        async with self._lock:
            return self._documents.get(str(Uri(_uri).normalized() if not isinstance(_uri, Uri) else _uri), None)

    def __len__(self) -> int:
        return self._documents.__len__()

    def __iter__(self) -> Iterator[DocumentUri]:
        return self._documents.__iter__()

    def __hash__(self) -> int:
        return id(self)

    async def _create_document(
        self,
        document_uri: DocumentUri,
        text: str,
        language_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> TextDocument:

        return TextDocument(
            document_uri=document_uri,
            language_id=language_id,
            text=text,
            version=version,
        )

    async def append_document(
        self,
        document_uri: DocumentUri,
        language_id: str,
        text: str,
        version: Optional[int] = None,
    ) -> TextDocument:

        async with self._lock:
            document = await self._create_document(
                document_uri=document_uri, language_id=language_id, text=text, version=version
            )

            self._documents[document_uri] = document

            return document

    __NORMALIZE_LINE_ENDINGS = re.compile(r"(\r?\n)")

    @classmethod
    def _normalize_line_endings(cls, text: str) -> str:
        return cls.__NORMALIZE_LINE_ENDINGS.sub("\n", text)

    @rpc_method(name="textDocument/didOpen", param_type=DidOpenTextDocumentParams)
    @_logger.call
    async def _text_document_did_open(self, text_document: TextDocumentItem, *args: Any, **kwargs: Any) -> None:
        async with self._lock:
            uri = str(Uri(text_document.uri).normalized())
            document = self._documents.get(uri, None)

            text_changed = True
            normalized_text = self._normalize_line_endings(text_document.text)

            if document is None:
                document = await self._create_document(
                    text_document.uri, normalized_text, text_document.language_id, text_document.version
                )

                self._documents[uri] = document
            else:
                text_changed = await document.text() != normalized_text
                if text_changed:
                    await document.apply_full_change(text_document.version, normalized_text)

            document.opened_in_editor = True
            document.references.add(self)

        await self.did_open(self, document, callback_filter=language_id_filter(document))

        if text_changed:
            await self.did_change(self, document, callback_filter=language_id_filter(document))

    @rpc_method(name="textDocument/didClose", param_type=DidCloseTextDocumentParams)
    @_logger.call
    async def _text_document_did_close(self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any) -> None:
        uri = str(Uri(text_document.uri).normalized())
        document = await self.get(uri)

        if document is not None:
            document.references.remove(self)
            document.opened_in_editor = False

            await self.close_document(document)
            await self.did_close(self, document, callback_filter=language_id_filter(document))

    @_logger.call
    async def close_document(self, document: TextDocument, ignore_references: bool = False) -> None:
        async with self._lock:
            if len(document.references) == 0 or ignore_references:
                self._documents.pop(str(document.uri), None)

                await document.clear()
                del document
            else:
                document._version = None
                if await document.revert(None):
                    await self.did_change(self, document, callback_filter=language_id_filter(document))

            gc.collect()

    @rpc_method(name="textDocument/willSave", param_type=WillSaveTextDocumentParams)
    @_logger.call
    async def _text_document_will_save(
        self, text_document: TextDocumentIdentifier, reason: TextDocumentSaveReason, *args: Any, **kwargs: Any
    ) -> None:
        # TODO: implement
        pass

    @rpc_method(name="textDocument/didSave", param_type=DidSaveTextDocumentParams)
    @_logger.call
    async def _text_document_did_save(
        self, text_document: TextDocumentIdentifier, text: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> None:
        document = await self.get(str(Uri(text_document.uri).normalized()))
        self._logger.warning(lambda: f"Document {text_document.uri} is not opened.", condition=lambda: document is None)

        if document is not None:
            if text is not None:
                normalized_text = self._normalize_line_endings(text)

                text_changed = await document.text() != normalized_text
                if text_changed:
                    await document.save(None, text)
                    await self.did_change(self, document, callback_filter=language_id_filter(document))

            await self.did_save(self, document, callback_filter=language_id_filter(document))

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
        document = await self.get(str(Uri(text_document.uri).normalized()))
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
                await document.apply_none_change()
            elif sync_kind == TextDocumentSyncKind.FULL and isinstance(
                content_change, TextDocumentContentTextChangeEvent
            ):
                await document.apply_full_change(
                    text_document.version, self._normalize_line_endings(content_change.text)
                )
            elif sync_kind == TextDocumentSyncKind.INCREMENTAL and isinstance(
                content_change, TextDocumentContentRangeChangeEvent
            ):
                await document.apply_incremental_change(
                    text_document.version, content_change.range, self._normalize_line_endings(content_change.text)
                )
            else:
                raise LanguageServerDocumentException(
                    f"Invalid type for content_changes {type(content_change)} "
                    f"and server capability {self.parent.capabilities.text_document_sync} "
                    f"for document {text_document.uri}."
                )

        await self.did_change(self, document, callback_filter=language_id_filter(document))
