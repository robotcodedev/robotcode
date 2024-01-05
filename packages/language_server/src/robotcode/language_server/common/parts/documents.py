from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Final,
    Iterator,
    List,
    Optional,
    Union,
)

from robotcode.core.event import event
from robotcode.core.lsp.types import (
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentUri,
    FileChangeType,
    FileEvent,
    TextDocumentContentChangeEvent,
    TextDocumentContentChangeEventType1,
    TextDocumentContentChangeEventType2,
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
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import JsonRPCException, rpc_method
from robotcode.language_server.common.decorators import language_id_filter
from robotcode.language_server.common.text_document import TextDocument

from .protocol_part import LanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


__all__ = ["TextDocumentProtocolPart", "LanguageServerDocumentError"]


class LanguageServerDocumentError(JsonRPCException):
    pass


class CantReadDocumentError(Exception):
    pass


class TextDocumentProtocolPart(LanguageServerProtocolPart):
    _logger: Final = LoggingDescriptor()

    def __init__(self, parent: LanguageServerProtocol) -> None:
        super().__init__(parent)
        self._documents: Dict[DocumentUri, TextDocument] = {}
        self.parent.on_initialized.add(self._protocol_initialized)
        self._lock = threading.RLock()

    @property
    def documents(self) -> List[TextDocument]:
        return list(self._documents.values())

    def _protocol_initialized(self, sender: Any) -> None:
        self._update_filewatchers()

    def _update_filewatchers(self) -> None:
        if self.parent.file_extensions:
            self.parent.workspace.add_file_watcher(
                self._file_watcher,
                f"**/*.{{{','.join(self.parent.file_extensions)}}}",
                WatchKind.CREATE | WatchKind.CHANGE | WatchKind.DELETE,
            )

    def _file_watcher(self, sender: Any, changes: List[FileEvent]) -> None:
        to_change: Dict[str, FileEvent] = {}
        for change in changes:
            to_change[change.uri] = change

        for change in to_change.values():
            if change.type == FileChangeType.CREATED:
                self.did_create_uri(self, change.uri)

            document = self._documents.get(DocumentUri(Uri(change.uri).normalized()), None)
            if document is not None and change.type == FileChangeType.CREATED:
                self.did_create(self, document, callback_filter=language_id_filter(document))

            elif document is not None and not document.opened_in_editor:
                if change.type == FileChangeType.DELETED:
                    self.close_document(document, True)
                    self.did_close(
                        self,
                        document,
                        callback_filter=language_id_filter(document),
                    )

                elif change.type == FileChangeType.CHANGED:
                    document.apply_full_change(
                        None,
                        self.read_document_text(document.uri, language_id_filter(document)),
                        save=True,
                    )
                    self.did_change(
                        self,
                        document,
                        callback_filter=language_id_filter(document),
                    )

    def read_document_text(self, uri: Uri, language_id: Union[str, Callable[[Any], bool], None]) -> str:
        for e in self.on_read_document_text(
            self,
            uri,
            callback_filter=language_id_filter(language_id) if isinstance(language_id, str) else language_id,
        ):
            if isinstance(e, BaseException):
                raise RuntimeError(f"Can't read document text from {uri}: {e}") from e

            if e is not None:
                return self._normalize_line_endings(e)

        raise FileNotFoundError(str(uri))

    def detect_language_id(self, path_or_uri: Union[str, os.PathLike[Any], Uri]) -> str:
        path = path_or_uri.to_path() if isinstance(path_or_uri, Uri) else Path(path_or_uri)

        for lang in self.parent.languages:
            if path.suffix in lang.extensions:
                return lang.id

        return "unknown"

    @_logger.call
    def get_or_open_document(
        self,
        path: Union[str, os.PathLike[Any]],
        language_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> TextDocument:
        uri = Uri.from_path(path).normalized()

        result = self.get(uri)
        if result is not None:
            return result

        try:
            return self.append_document(
                document_uri=DocumentUri(uri),
                language_id=language_id or self.detect_language_id(path),
                text=self.read_document_text(uri, language_id),
                version=version,
            )
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            raise CantReadDocumentError(f"Error reading document '{path}': {e!s}") from e

    @event
    def on_read_document_text(sender, uri: Uri) -> Optional[str]:
        ...

    @event
    def did_create_uri(sender, uri: DocumentUri) -> None:
        ...

    @event
    def did_create(sender, document: TextDocument) -> None:
        ...

    @event
    def did_open(sender, document: TextDocument) -> None:
        ...

    @event
    def did_close(sender, document: TextDocument) -> None:
        ...

    @event
    def did_change(sender, document: TextDocument) -> None:
        ...

    @event
    def did_save(sender, document: TextDocument) -> None:
        ...

    def get(self, _uri: Union[DocumentUri, Uri]) -> Optional[TextDocument]:
        with self._lock:
            return self._documents.get(
                str(Uri(_uri).normalized() if not isinstance(_uri, Uri) else _uri),
                None,
            )

    def __len__(self) -> int:
        return self._documents.__len__()

    def __iter__(self) -> Iterator[DocumentUri]:
        return self._documents.__iter__()

    def __hash__(self) -> int:
        return id(self)

    def _create_document(
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

    def append_document(
        self,
        document_uri: DocumentUri,
        language_id: str,
        text: str,
        version: Optional[int] = None,
    ) -> TextDocument:
        with self._lock:
            document = self._create_document(
                document_uri=document_uri,
                language_id=language_id,
                text=text,
                version=version,
            )

            self._documents[document_uri] = document

            return document

    __NORMALIZE_LINE_ENDINGS: Final = re.compile(r"(\r?\n)")

    @classmethod
    def _normalize_line_endings(cls, text: str) -> str:
        return cls.__NORMALIZE_LINE_ENDINGS.sub("\n", text)

    @rpc_method(name="textDocument/didOpen", param_type=DidOpenTextDocumentParams)
    @_logger.call
    def _text_document_did_open(self, text_document: TextDocumentItem, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            uri = str(Uri(text_document.uri).normalized())
            document = self._documents.get(uri, None)

            normalized_text = self._normalize_line_endings(text_document.text)

            if document is None:
                text_changed = False
                document = self._create_document(
                    text_document.uri,
                    normalized_text,
                    text_document.language_id
                    if text_document.language_id
                    else self.detect_language_id(text_document.uri),
                    text_document.version,
                )

                self._documents[uri] = document
            else:
                text_changed = document.text() != normalized_text
                if text_changed:
                    document.apply_full_change(text_document.version, normalized_text)
                else:
                    document.version = text_document.version

            document.opened_in_editor = True

            self.did_open(self, document, callback_filter=language_id_filter(document))

        if text_changed:
            self.did_change(self, document, callback_filter=language_id_filter(document))

    @rpc_method(name="textDocument/didClose", param_type=DidCloseTextDocumentParams)
    @_logger.call
    def _text_document_did_close(self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any) -> None:
        uri = str(Uri(text_document.uri).normalized())
        document = self.get(uri)

        if document is not None:
            document.opened_in_editor = False

            self.close_document(document)

            document.version = None

            self.did_close(self, document, callback_filter=language_id_filter(document))

    @_logger.call
    def close_document(self, document: TextDocument, real_close: bool = False) -> None:
        if real_close:
            with self._lock:
                self._documents.pop(str(document.uri), None)

            document.clear()
        else:
            document._version = None
            if document.revert(None):
                self.did_change(self, document, callback_filter=language_id_filter(document))

    @rpc_method(name="textDocument/willSave", param_type=WillSaveTextDocumentParams)
    @_logger.call
    def _text_document_will_save(
        self,
        text_document: TextDocumentIdentifier,
        reason: TextDocumentSaveReason,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # TODO: implement
        pass

    @rpc_method(name="textDocument/didSave", param_type=DidSaveTextDocumentParams)
    @_logger.call
    def _text_document_did_save(
        self,
        text_document: TextDocumentIdentifier,
        text: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        document = self.get(str(Uri(text_document.uri).normalized()))
        self._logger.warning(
            lambda: f"Document {text_document.uri} is not opened.",
            condition=lambda: document is None,
        )

        if document is not None:
            if text is not None:
                normalized_text = self._normalize_line_endings(text)

                text_changed = document.text() != normalized_text
                if text_changed:
                    document.save(None, text)
                    self.did_change(
                        self,
                        document,
                        callback_filter=language_id_filter(document),
                    )

            self.did_save(self, document, callback_filter=language_id_filter(document))

    @rpc_method(
        name="textDocument/willSaveWaitUntil",
        param_type=WillSaveTextDocumentParams,
    )
    @_logger.call
    def _text_document_will_save_wait_until(
        self,
        text_document: TextDocumentIdentifier,
        reason: TextDocumentSaveReason,
        *args: Any,
        **kwargs: Any,
    ) -> List[TextEdit]:
        return []

    @rpc_method(name="textDocument/didChange", param_type=DidChangeTextDocumentParams)
    @_logger.call
    def _text_document_did_change(
        self,
        text_document: VersionedTextDocumentIdentifier,
        content_changes: List[TextDocumentContentChangeEvent],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        document = self.get(str(Uri(text_document.uri).normalized()))
        if document is None:
            raise LanguageServerDocumentError(f"Document {text_document.uri} is not opened.")

        sync_kind = (
            self.parent.capabilities.text_document_sync
            if isinstance(
                self.parent.capabilities.text_document_sync,
                TextDocumentSyncKind,
            )
            else self.parent.capabilities.text_document_sync.change
            if isinstance(
                self.parent.capabilities.text_document_sync,
                TextDocumentSyncOptions,
            )
            else None
        )
        for content_change in content_changes:
            if sync_kind is None or sync_kind == TextDocumentSyncKind.NONE_:
                document.apply_none_change()
            elif sync_kind == TextDocumentSyncKind.FULL and isinstance(
                content_change, TextDocumentContentChangeEventType2
            ):
                document.apply_full_change(
                    text_document.version,
                    self._normalize_line_endings(content_change.text),
                )
            elif sync_kind == TextDocumentSyncKind.INCREMENTAL and isinstance(
                content_change, TextDocumentContentChangeEventType1
            ):
                document.apply_incremental_change(
                    text_document.version,
                    content_change.range,
                    self._normalize_line_endings(content_change.text),
                )
            else:
                raise LanguageServerDocumentError(
                    f"Invalid type for content_changes {type(content_change)} "
                    f"and server capability {self.parent.capabilities.text_document_sync} "
                    f"for document {text_document.uri}."
                )

        self.did_change(self, document, callback_filter=language_id_filter(document))
