from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
    cast,
)

from ....jsonrpc2.protocol import JsonRPCException, rpc_method
from ....utils.async_tools import (
    Lock,
    async_event,
    async_tasking_event,
    create_sub_task,
)
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ..decorators import language_id_filter
from ..lsp_types import (
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentUri,
    FileChangeType,
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


class CantReadDocumentException(Exception):
    pass


class TextDocumentProtocolPart(LanguageServerProtocolPart):

    _logger = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}
        self.parent.on_initialized.add(self._protocol_initialized)
        self._lock = Lock()

    @property
    def documents(self) -> List[TextDocument]:
        return list(self._documents.values())

    async def _protocol_initialized(self, sender: Any) -> None:
        await self._update_filewatchers()

    async def _update_filewatchers(self) -> None:
        if self.parent.file_extensions:
            await self.parent.workspace.add_file_watcher(
                self._file_watcher,
                f"**/*.{{{','.join(self.parent.file_extensions)}}}",
                WatchKind.CREATE | WatchKind.CHANGE | WatchKind.DELETE,
            )

    async def _file_watcher(self, sender: Any, changes: List[FileEvent]) -> None:
        to_change: Dict[str, FileEvent] = {}
        for change in changes:
            to_change[change.uri] = change

        for change in to_change.values():
            if change.type == FileChangeType.CREATED:
                create_sub_task(self.did_create_uri(self, change.uri), loop=self.parent.loop)

            document = self._documents.get(DocumentUri(Uri(change.uri).normalized()), None)
            if document is not None and change.type == FileChangeType.CREATED:
                create_sub_task(
                    self.did_create(self, document, callback_filter=language_id_filter(document)), loop=self.parent.loop
                )
            elif document is not None and not document.opened_in_editor:
                if change.type == FileChangeType.DELETED:
                    await self.close_document(document, True)
                    create_sub_task(
                        self.did_close(self, document, callback_filter=language_id_filter(document)),
                        loop=self.parent.loop,
                    )
                elif change.type == FileChangeType.CHANGED:
                    document.apply_full_change(
                        None, await self.read_document_text(document.uri, language_id_filter(document)), save=True
                    )
                    create_sub_task(
                        self.did_change(self, document, callback_filter=language_id_filter(document)),
                        loop=self.parent.loop,
                    )

    async def read_document_text(self, uri: Uri, language_id: Union[str, Callable[[Any], bool], None]) -> str:
        for e in await self.on_read_document_text(
            self, uri, callback_filter=language_id_filter(language_id) if isinstance(language_id, str) else language_id
        ):
            if e is not None:
                return self._normalize_line_endings(cast(str, e))

        raise FileNotFoundError(str(uri))

    def detect_language_id(self, path_or_uri: Union[str, os.PathLike[Any], Uri]) -> str:
        path = path_or_uri.to_path() if isinstance(path_or_uri, Uri) else Path(path_or_uri)

        for lang in self.parent.languages:
            if path.suffix in lang.extensions:
                return lang.id

        return "unknown"

    @_logger.call
    async def get_or_open_document(
        self, path: Union[str, os.PathLike[Any]], language_id: Optional[str] = None, version: Optional[int] = None
    ) -> TextDocument:
        uri = Uri.from_path(path).normalized()

        result = await self.get(uri)
        if result is not None:
            return result

        try:
            return await self.parent.documents.append_document(
                document_uri=DocumentUri(uri),
                language_id=language_id or self.detect_language_id(path),
                text=await self.read_document_text(uri, language_id),
                version=version,
            )
        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as e:
            raise CantReadDocumentException(f"Error reading document '{path}': {str(e)}") from e

    @async_event
    async def on_read_document_text(sender, uri: Uri) -> Optional[str]:  # NOSONAR
        ...

    @async_tasking_event
    async def did_append_document(sender, document: TextDocument) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def did_create_uri(sender, uri: DocumentUri) -> None:  # NOSONAR
        ...

    @async_tasking_event
    async def did_create(sender, document: TextDocument) -> None:  # NOSONAR
        ...

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

    def get_sync(self, _uri: Union[DocumentUri, Uri]) -> Optional[TextDocument]:
        return self._documents.get(str(Uri(_uri).normalized() if not isinstance(_uri, Uri) else _uri), None)

    async def get(self, _uri: Union[DocumentUri, Uri]) -> Optional[TextDocument]:
        async with self._lock:
            return self.get_sync(_uri)

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

            create_sub_task(
                self.did_append_document(self, document, callback_filter=language_id_filter(document)),
                loop=self.parent.loop,
            )

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

            normalized_text = self._normalize_line_endings(text_document.text)

            if document is None:
                text_changed = False
                document = await self._create_document(
                    text_document.uri, normalized_text, text_document.language_id, text_document.version
                )

                self._documents[uri] = document
            else:
                text_changed = document.text() != normalized_text
                if text_changed:
                    document.apply_full_change(text_document.version, normalized_text)

            document.opened_in_editor = True

        create_sub_task(
            self.did_open(self, document, callback_filter=language_id_filter(document)), loop=self.parent.loop
        )

        if text_changed:
            create_sub_task(
                self.did_change(self, document, callback_filter=language_id_filter(document)),
                loop=self.parent.loop,
            )

    @rpc_method(name="textDocument/didClose", param_type=DidCloseTextDocumentParams)
    @_logger.call
    async def _text_document_did_close(self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any) -> None:
        uri = str(Uri(text_document.uri).normalized())
        document = await self.get(uri)

        if document is not None:
            document.opened_in_editor = False

            await self.close_document(document)

            document.version = None

            create_sub_task(
                self.did_close(self, document, callback_filter=language_id_filter(document)), loop=self.parent.loop
            )

    @_logger.call
    async def close_document(self, document: TextDocument, real_close: bool = False) -> None:
        if real_close:
            async with self._lock:
                self._documents.pop(str(document.uri), None)

            document.clear()
            del document
        else:
            document._version = None
            if document.revert(None):
                create_sub_task(
                    self.did_change(self, document, callback_filter=language_id_filter(document)), loop=self.parent.loop
                )

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

                text_changed = document.text() != normalized_text
                if text_changed:
                    document.save(None, text)
                    create_sub_task(
                        self.did_change(self, document, callback_filter=language_id_filter(document)),
                        loop=self.parent.loop,
                    )

            create_sub_task(
                self.did_save(self, document, callback_filter=language_id_filter(document)), loop=self.parent.loop
            )

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
        document = self.get_sync(str(Uri(text_document.uri).normalized()))
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
                document.apply_none_change()
            elif sync_kind == TextDocumentSyncKind.FULL and isinstance(
                content_change, TextDocumentContentTextChangeEvent
            ):
                document.apply_full_change(text_document.version, self._normalize_line_endings(content_change.text))
            elif sync_kind == TextDocumentSyncKind.INCREMENTAL and isinstance(
                content_change, TextDocumentContentRangeChangeEvent
            ):
                document.apply_incremental_change(
                    text_document.version, content_change.range, self._normalize_line_endings(content_change.text)
                )
            else:
                raise LanguageServerDocumentException(
                    f"Invalid type for content_changes {type(content_change)} "
                    f"and server capability {self.parent.capabilities.text_document_sync} "
                    f"for document {text_document.uri}."
                )

        create_sub_task(
            self.did_change(self, document, callback_filter=language_id_filter(document)), loop=self.parent.loop
        )
